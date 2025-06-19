"""
Flask Application Factory
"""
from flask import Flask
from flask_cors import CORS
import os
from config.settings import Config
from utils.logger import setup_logger
from utils.file_manager import FileManager


def create_app(config_name='default'):
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config.get_config(config_name))
    
    # Initialize extensions
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Setup logging
    setup_logger(app)
    
    # Initialize file manager
    file_manager = FileManager(app.config)
    file_manager.ensure_directories()
    
    # Register blueprints
    from app.routes.transcription import transcription_bp
    from app.routes.jobs import jobs_bp
    from app.routes.history import history_bp
    from app.routes.admin import admin_bp
    
    app.register_blueprint(transcription_bp, url_prefix='/api/v1')
    app.register_blueprint(jobs_bp, url_prefix='/api/v1')
    app.register_blueprint(history_bp, url_prefix='/api/v1')
    app.register_blueprint(admin_bp, url_prefix='/api/v1/admin')
    
    # Register middleware
    from app.middleware.validation import register_validation_handlers
    from app.middleware.rate_limit import register_rate_limit
    
    register_validation_handlers(app)
    register_rate_limit(app)
    
    # Root route
    @app.route('/')
    def index():
        return {
            'name': 'Advanced Speech-to-Text API',
            'version': app.config['API_VERSION'],
            'description': 'A comprehensive speech recognition API with advanced features',
            'status': 'running',
            'endpoints': {
                'transcription': '/api/v1/transcribe',
                'async_transcription': '/api/v1/transcribe/async',
                'job_status': '/api/v1/jobs/<job_id>',
                'history': '/api/v1/history',
                'stats': '/api/v1/admin/stats',
                'health': '/api/v1/health'
            },
            'documentation': '/docs'
        }
    
    @app.route('/api/v1/health')
    def health_check():
        """Health check endpoint"""
        from datetime import datetime
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': app.config['API_VERSION']
        }
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return {'error': 'Bad request', 'message': str(error)}, 400
    
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found', 'message': 'The requested resource was not found'}, 404
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return {'error': 'File too large', 'message': f'Maximum file size is {app.config["MAX_CONTENT_LENGTH"] // (1024*1024)}MB'}, 413
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Internal server error: {error}')
        return {'error': 'Internal server error', 'message': 'An unexpected error occurred'}, 500
    
    return app