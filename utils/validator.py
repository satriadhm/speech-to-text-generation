"""
Request Validation Utilities
"""
from werkzeug.datastructures import FileStorage
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def validate_file(file: FileStorage, config: dict) -> dict:
    """Validate uploaded file"""
    try:
        if not file or not file.filename:
            return {
                'valid': False,
                'message': 'No file provided'
            }
        
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        max_size = config.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024)
        if file_size > max_size:
            return {
                'valid': False,
                'message': f'File too large. Maximum size: {max_size // (1024*1024)}MB'
            }
        
        if file_size == 0:
            return {
                'valid': False,
                'message': 'File is empty'
            }
        
        file_ext = Path(file.filename).suffix.lower().lstrip('.')
        allowed_extensions = config.get('ALLOWED_EXTENSIONS', {})
        
        all_extensions = set()
        for ext_list in allowed_extensions.values():
            all_extensions.update(ext_list)
        
        if file_ext not in all_extensions:
            return {
                'valid': False,
                'message': f'Unsupported file type: {file_ext}. Supported: {", ".join(sorted(all_extensions))}'
            }
        
        return {
            'valid': True,
            'message': 'File is valid',
            'file_size': file_size,
            'file_extension': file_ext
        }
        
    except Exception as e:
        logger.error(f"File validation error: {e}")
        return {
            'valid': False,
            'message': f'Validation error: {str(e)}'
        }

def validate_language(language: str, config: dict) -> bool:
    """Validate language code"""
    try:
        supported_languages = config.get('SUPPORTED_LANGUAGES', {})
        return language in supported_languages
    except Exception:
        return False

def validate_transcription_params(params: dict) -> dict:
    """Validate transcription parameters"""
    errors = []
    warnings = []
    
    language = params.get('language')
    if language and not isinstance(language, str):
        errors.append('Language must be a string')
    
    enhance_audio = params.get('enhance_audio')
    if enhance_audio is not None:
        if isinstance(enhance_audio, str):
            if enhance_audio.lower() not in ['true', 'false']:
                errors.append('enhance_audio must be "true" or "false"')
        elif not isinstance(enhance_audio, bool):
            errors.append('enhance_audio must be boolean or string')
    
    callback_url = params.get('callback_url')
    if callback_url:
        if not isinstance(callback_url, str):
            errors.append('callback_url must be a string')
        elif not callback_url.startswith(('http://', 'https://')):
            errors.append('callback_url must be a valid HTTP/HTTPS URL')
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    try:
        import re
        
        safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
        safe_filename = re.sub(r'_+', '_', safe_filename)
        safe_filename = safe_filename.strip('_.')
        if not safe_filename:
            safe_filename = 'unnamed_file'
        if len(safe_filename) > 100:
            name_part = safe_filename[:95]
            ext_part = Path(safe_filename).suffix
            safe_filename = name_part + ext_part
        return safe_filename
        
    except Exception:
        return 'unnamed_file'

def validate_pagination_params(page: str, per_page: str) -> dict:
    """Validate pagination parameters"""
    try:
        try:
            page_num = int(page) if page else 1
            if page_num < 1:
                page_num = 1
        except (ValueError, TypeError):
            page_num = 1
        
        try:
            per_page_num = int(per_page) if per_page else 20
            if per_page_num < 1:
                per_page_num = 20
            elif per_page_num > 100:
                per_page_num = 100
        except (ValueError, TypeError):
            per_page_num = 20
        
        return {
            'valid': True,
            'page': page_num,
            'per_page': per_page_num
        }
        
    except Exception as e:
        logger.error(f"Pagination validation error: {e}")
        return {
            'valid': True,
            'page': 1,
            'per_page': 20
        }
