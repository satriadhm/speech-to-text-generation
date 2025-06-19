"""
Configuration settings for the Speech-to-Text API
"""
import os
from datetime import timedelta
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

class BaseConfig:
    """Base configuration"""
    # API Info
    API_VERSION = "2.0.0"
    API_TITLE = "Advanced Speech-to-Text API"
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # File upload settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_FILE_SIZE', 100 * 1024 * 1024))  # 100MB
    UPLOAD_FOLDER = BASE_DIR / 'storage' / 'uploads'
    OUTPUT_FOLDER = BASE_DIR / 'storage' / 'outputs'
    TEMP_FOLDER = BASE_DIR / 'storage' / 'temp'
    LOG_FOLDER = BASE_DIR / 'storage' / 'logs'
    
    # Supported file extensions
    ALLOWED_EXTENSIONS = {
        'audio': {'wav', 'mp3', 'flac', 'm4a', 'ogg', 'webm'},
        'video': {'mp4', 'avi', 'mov', 'mkv', 'webm'}
    }
    
    # Speech recognition settings
    SUPPORTED_LANGUAGES = {
        'id-ID': {'name': 'Indonesian', 'region': 'Indonesia'},
        'en-US': {'name': 'English', 'region': 'United States'},
        'en-GB': {'name': 'English', 'region': 'United Kingdom'},
        'en-AU': {'name': 'English', 'region': 'Australia'},
        'es-ES': {'name': 'Spanish', 'region': 'Spain'},
        'es-MX': {'name': 'Spanish', 'region': 'Mexico'},
        'fr-FR': {'name': 'French', 'region': 'France'},
        'de-DE': {'name': 'German', 'region': 'Germany'},
        'it-IT': {'name': 'Italian', 'region': 'Italy'},
        'ja-JP': {'name': 'Japanese', 'region': 'Japan'},
        'ko-KR': {'name': 'Korean', 'region': 'South Korea'},
        'zh-CN': {'name': 'Chinese', 'region': 'China (Simplified)'},
        'zh-TW': {'name': 'Chinese', 'region': 'Taiwan (Traditional)'},
        'pt-BR': {'name': 'Portuguese', 'region': 'Brazil'},
        'pt-PT': {'name': 'Portuguese', 'region': 'Portugal'},
        'ru-RU': {'name': 'Russian', 'region': 'Russia'},
        'ar-SA': {'name': 'Arabic', 'region': 'Saudi Arabia'},
        'hi-IN': {'name': 'Hindi', 'region': 'India'},
        'th-TH': {'name': 'Thai', 'region': 'Thailand'},
        'vi-VN': {'name': 'Vietnamese', 'region': 'Vietnam'},
        'tr-TR': {'name': 'Turkish', 'region': 'Turkey'},
        'nl-NL': {'name': 'Dutch', 'region': 'Netherlands'},
        'sv-SE': {'name': 'Swedish', 'region': 'Sweden'},
        'da-DK': {'name': 'Danish', 'region': 'Denmark'},
        'no-NO': {'name': 'Norwegian', 'region': 'Norway'},
        'fi-FI': {'name': 'Finnish', 'region': 'Finland'}
    }
    
    DEFAULT_LANGUAGE = 'id-ID'
    
    # Audio processing settings
    AUDIO_SAMPLE_RATE = 16000
    AUDIO_CHANNELS = 1  # Mono
    AUDIO_FORMAT = 'wav'
    
    # Job management
    MAX_CONCURRENT_JOBS = int(os.environ.get('MAX_CONCURRENT_JOBS', 5))
    JOB_TIMEOUT = int(os.environ.get('JOB_TIMEOUT', 600))  # 10 minutes
    JOB_CLEANUP_INTERVAL = int(os.environ.get('JOB_CLEANUP_INTERVAL', 3600))  # 1 hour
    
    # Rate limiting
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', 100))
    RATE_LIMIT_PERIOD = int(os.environ.get('RATE_LIMIT_PERIOD', 3600))  # 1 hour
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10 * 1024 * 1024))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    
    # Cache settings
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'memory')  # memory, redis
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))  # 5 minutes
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Database settings (for future use)
    DATABASE_URL = os.environ.get('DATABASE_URL', f'sqlite:///{BASE_DIR}/app.db')
    
    # Webhook settings
    WEBHOOK_ENABLED = os.environ.get('WEBHOOK_ENABLED', 'false').lower() == 'true'
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
    WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')
    
    # Monitoring
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    PROMETHEUS_ENABLED = os.environ.get('PROMETHEUS_ENABLED', 'false').lower() == 'true'


class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    LOG_LEVEL = 'DEBUG'
    RATE_LIMIT_ENABLED = False


class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Stricter security settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')
    
    # Enhanced logging
    LOG_LEVEL = 'INFO'
    
    # Enable all security features
    RATE_LIMIT_ENABLED = True
    WEBHOOK_ENABLED = True


class TestingConfig(BaseConfig):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    RATE_LIMIT_ENABLED = False
    
    # Use temporary directories for testing
    UPLOAD_FOLDER = BASE_DIR / 'tests' / 'temp' / 'uploads'
    OUTPUT_FOLDER = BASE_DIR / 'tests' / 'temp' / 'outputs'
    TEMP_FOLDER = BASE_DIR / 'tests' / 'temp' / 'temp'
    LOG_FOLDER = BASE_DIR / 'tests' / 'temp' / 'logs'


class Config:
    """Configuration factory"""
    
    @staticmethod
    def get_config(config_name=None):
        """Get configuration based on environment"""
        if config_name is None:
            config_name = os.environ.get('FLASK_ENV', 'development')
        
        config_map = {
            'development': DevelopmentConfig,
            'production': ProductionConfig,
            'testing': TestingConfig,
            'default': DevelopmentConfig
        }
        
        return config_map.get(config_name, DevelopmentConfig)