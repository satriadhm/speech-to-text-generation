"""
Logging Configuration and Setup
"""
import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime

def setup_logger(app):
    """Setup application logging"""
    try:
        log_folder = Path(app.config.get('LOG_FOLDER', 'storage/logs'))
        log_folder.mkdir(parents=True, exist_ok=True)
        
        log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper())
        log_format = app.config.get('LOG_FORMAT', 
                                   '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        max_bytes = app.config.get('LOG_MAX_BYTES', 10 * 1024 * 1024)
        backup_count = app.config.get('LOG_BACKUP_COUNT', 5)
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[]
        )
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(log_format)
        console_handler.setFormatter(console_formatter)
        
        log_file = log_folder / 'app.log'
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        
        error_log_file = log_folder / 'error.log'
        error_handler = logging.handlers.RotatingFileHandler(
            filename=str(error_log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(error_handler)
        
        app.logger.setLevel(log_level)
        app.logger.info("Logging configured successfully")
        
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.setLevel(logging.WARNING)
        
        return True
        
    except Exception as e:
        print(f"Failed to setup logging: {e}")
        return False

def get_logger(name: str):
    """Get a logger instance"""
    return logging.getLogger(name)

class RequestLogger:
    """Middleware for logging HTTP requests"""
    
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger('request_logger')
    
    def __call__(self, environ, start_response):
        def new_start_response(status, response_headers):
            method = environ.get('REQUEST_METHOD', 'Unknown')
            path = environ.get('PATH_INFO', '')
            query_string = environ.get('QUERY_STRING', '')
            remote_addr = environ.get('REMOTE_ADDR', '')
            user_agent = environ.get('HTTP_USER_AGENT', '')
            
            full_path = f"{path}?{query_string}" if query_string else path
            
            self.logger.info(
                f"{remote_addr} - \"{method} {full_path}\" {status} - \"{user_agent}\""
            )
            
            return start_response(status, response_headers)
        
        return self.app(environ, new_start_response)

def log_function_call(func_name: str, args: dict = None, kwargs: dict = None):
    """Decorator for logging function calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            
            logger.debug(f"Entering {func_name}")
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Exiting {func_name} successfully")
                return result
            except Exception as e:
                logger.error(f"Error in {func_name}: {e}")
                raise
        
        return wrapper
    return decorator

def setup_performance_logging(app):
    """Setup performance logging"""
    import time
    
    @app.before_request
    def before_request():
        from flask import g
        g.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        from flask import g, request
        
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            
            if duration > 1.0:
                app.logger.warning(
                    f"Slow request: {request.method} {request.path} took {duration:.2f}s"
                )
            
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
        
        return response

def log_error_details(app):
    """Setup detailed error logging"""
    
    @app.errorhandler(Exception)
    def log_exception(error):
        import traceback
        from flask import request
        
        app.logger.error(f"""
Request that caused error:
Method: {request.method}
URL: {request.url}
Headers: {dict(request.headers)}
Data: {request.get_data(as_text=True) if request.content_length and request.content_length < 1024 else 'Too large to log'}

Exception: {str(error)}
Traceback:
{traceback.format_exc()}
        """)
        
        raise error
