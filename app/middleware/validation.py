"""
Validation Middleware
"""
from flask import request, jsonify, current_app
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def register_validation_handlers(app):
    """Register validation error handlers"""
    
    @app.errorhandler(413)
    def file_too_large(error):
        max_size = app.config.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024)
        return jsonify({
            'error': 'File too large',
            'message': f'Maximum file size is {max_size // (1024*1024)}MB',
            'code': 413
        }), 413
    
    @app.errorhandler(415)
    def unsupported_media_type(error):
        return jsonify({
            'error': 'Unsupported media type',
            'message': 'The uploaded file type is not supported',
            'code': 415
        }), 415

def validate_content_type(allowed_types):
    """Decorator to validate request content type"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            content_type = request.content_type
            
            if content_type and not any(ct in content_type for ct in allowed_types):
                return jsonify({
                    'error': 'Invalid content type',
                    'message': f'Expected one of: {", ".join(allowed_types)}',
                    'received': content_type
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_json_request(required_fields=None):
    """Decorator to validate JSON request data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'error': 'Invalid request',
                    'message': 'Request must be JSON'
                }), 400
            
            data = request.get_json()
            if not data:
                return jsonify({
                    'error': 'Invalid request',
                    'message': 'Request body is empty or invalid JSON'
                }), 400
            
            # Check required fields
            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field not in data:
                        missing_fields.append(field)
                
                if missing_fields:
                    return jsonify({
                        'error': 'Missing required fields',
                        'message': f'Required fields: {", ".join(missing_fields)}'
                    }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_file_upload(allowed_extensions=None, max_size=None):
    """Decorator to validate file uploads"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if file is present
            if 'audio' not in request.files and 'file' not in request.files:
                return jsonify({
                    'error': 'No file uploaded',
                    'message': 'Please upload an audio file'
                }), 400
            
            file = request.files.get('audio') or request.files.get('file')
            
            if not file or file.filename == '':
                return jsonify({
                    'error': 'No file selected',
                    'message': 'Please select a file to upload'
                }), 400
            
            # Validate file extension
            if allowed_extensions:
                file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                if file_ext not in allowed_extensions:
                    return jsonify({
                        'error': 'Invalid file type',
                        'message': f'Allowed types: {", ".join(allowed_extensions)}',
                        'received': file_ext
                    }), 400
            
            # Validate file size
            if max_size:
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Reset
                
                if file_size > max_size:
                    return jsonify({
                        'error': 'File too large',
                        'message': f'Maximum size: {max_size // (1024*1024)}MB',
                        'received_size': f'{file_size // (1024*1024)}MB'
                    }), 413
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_language_param():
    """Decorator to validate language parameter"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            language = request.form.get('language') or request.args.get('language')
            
            if language:
                supported_languages = current_app.config.get('SUPPORTED_LANGUAGES', {})
                if language not in supported_languages:
                    return jsonify({
                        'error': 'Unsupported language',
                        'message': f'Language "{language}" is not supported',
                        'supported_languages': list(supported_languages.keys())
                    }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class RequestValidator:
    """Class-based request validator"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize validator with Flask app"""
        app.before_request(self.before_request)
    
    def before_request(self):
        """Run before each request"""
        logger.info(f"Request: {request.method} {request.path}")
        
        if request.content_length:
            max_size = current_app.config.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024)
            if request.content_length > max_size:
                return jsonify({
                    'error': 'Request too large',
                    'message': f'Maximum request size: {max_size // (1024*1024)}MB'
                }), 413
        
        @current_app.after_request
        def add_security_headers(response):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            return response