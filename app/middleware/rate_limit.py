"""
Rate Limiting Middleware
"""
import time
import json
from collections import defaultdict, deque
from flask import request, jsonify, current_app, g
from functools import wraps
import threading
import logging

logger = logging.getLogger(__name__)

class MemoryRateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = defaultdict(deque)
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple:
        """
        Check if request is allowed
        Returns (is_allowed, remaining_requests, reset_time)
        """
        with self.lock:
            now = time.time()
            window_start = now - window
            
            while self.requests[key] and self.requests[key][0] < window_start:
                self.requests[key].popleft()
            
            current_requests = len(self.requests[key])
            
            if current_requests >= limit:
                if self.requests[key]:
                    reset_time = self.requests[key][0] + window
                else:
                    reset_time = now + window
                
                return False, 0, reset_time
            
            self.requests[key].append(now)
            remaining = limit - current_requests - 1
            reset_time = now + window
            
            return True, remaining, reset_time
    
    def cleanup_old_entries(self):
        """Clean up old entries to prevent memory leaks"""
        with self.lock:
            now = time.time()
            keys_to_remove = []
            
            for key, requests in self.requests.items():
                while requests and requests[0] < now - 3600:
                    requests.popleft()
                
                if not requests:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.requests[key]

rate_limiter = MemoryRateLimiter()

def get_client_id():
    """Get client identifier for rate limiting"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        ip = request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    elif request.environ.get('HTTP_X_REAL_IP'):
        ip = request.environ['HTTP_X_REAL_IP']
    else:
        ip = request.environ.get('REMOTE_ADDR', 'unknown')
    
    return f"ip:{ip}"

def apply_rate_limit(limit: int = None, window: int = None, per: str = 'ip'):
    """
    Apply rate limiting to a route
    
    Args:
        limit: Number of requests allowed
        window: Time window in seconds
        per: What to rate limit by ('ip', 'user', etc.)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_app.config.get('RATE_LIMIT_ENABLED', True):
                return f(*args, **kwargs)
            
            request_limit = limit or current_app.config.get('RATE_LIMIT_REQUESTS', 100)
            time_window = window or current_app.config.get('RATE_LIMIT_PERIOD', 3600)
            
            if per == 'ip':
                client_id = get_client_id()
            else:
                client_id = f"{per}:{get_client_id()}"
            
            allowed, remaining, reset_time = rate_limiter.is_allowed(
                client_id, request_limit, time_window
            )
            
            @current_app.after_request
            def add_rate_limit_headers(response):
                response.headers['X-RateLimit-Limit'] = str(request_limit)
                response.headers['X-RateLimit-Remaining'] = str(remaining)
                response.headers['X-RateLimit-Reset'] = str(int(reset_time))
                response.headers['X-RateLimit-Window'] = str(time_window)
                return response
            
            if not allowed:
                retry_after = int(reset_time - time.time())
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {request_limit} per {time_window} seconds',
                    'retry_after': retry_after,
                    'limit': request_limit,
                    'window': time_window
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(retry_after)
                return response
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def register_rate_limit(app):
    """Register rate limiting with Flask app"""
    
    @app.before_request
    def global_rate_limit():
        skip_paths = ['/health', '/api/v1/health', '/api/v1/info']
        if request.path in skip_paths:
            return
        
        if not app.config.get('RATE_LIMIT_ENABLED', True):
            return
        
        global_limit = app.config.get('RATE_LIMIT_REQUESTS', 100)
        global_window = app.config.get('RATE_LIMIT_PERIOD', 3600)
        
        client_id = f"global:{get_client_id()}"
        allowed, remaining, reset_time = rate_limiter.is_allowed(
            client_id, global_limit, global_window
        )
        
        # Store in g for use in after_request
        g.rate_limit_remaining = remaining
        g.rate_limit_reset = reset_time
        g.rate_limit_limit = global_limit
        
        if not allowed:
            retry_after = int(reset_time - time.time())
            response = jsonify({
                'error': 'Global rate limit exceeded',
                'message': f'Too many requests. Global limit: {global_limit} per {global_window} seconds',
                'retry_after': retry_after
            })
            response.status_code = 429
            response.headers['Retry-After'] = str(retry_after)
            return response
    
    @app.after_request
    def add_global_rate_limit_headers(response):
        """Add rate limit headers to all responses"""
        if hasattr(g, 'rate_limit_remaining'):
            response.headers['X-RateLimit-Limit'] = str(g.rate_limit_limit)
            response.headers['X-RateLimit-Remaining'] = str(g.rate_limit_remaining)
            response.headers['X-RateLimit-Reset'] = str(int(g.rate_limit_reset))
        return response
    
    def cleanup_rate_limiter():
        """Background task to cleanup rate limiter"""
        import threading
        import time
        
        def cleanup_worker():
            while True:
                try:
                    time.sleep(300)
                    rate_limiter.cleanup_old_entries()
                    logger.debug("Rate limiter cleaned up")
                except Exception as e:
                    logger.error(f"Rate limiter cleanup error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("Rate limiter cleanup thread started")
    
    cleanup_rate_limiter()

def transcription_rate_limit():
    """Rate limiter for transcription endpoints"""
    return apply_rate_limit(limit=10, window=3600)

def job_status_rate_limit():
    """Rate limiter for job status endpoints"""
    return apply_rate_limit(limit=60, window=3600)

def upload_rate_limit():
    """Rate limiter for file uploads"""
    return apply_rate_limit(limit=5, window=3600)