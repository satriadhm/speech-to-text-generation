"""
File Management System for Upload and Storage
"""
import os
import shutil
import tempfile
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import logging
from datetime import datetime, timedelta
import threading
import time

logger = logging.getLogger(__name__)

class FileManager:
    """File management system for handling uploads and temporary files"""
    
    def __init__(self, config):
        self.config = config
        
        self.upload_folder = Path(config.get('UPLOAD_FOLDER', 'storage/uploads'))
        self.output_folder = Path(config.get('OUTPUT_FOLDER', 'storage/outputs'))
        self.temp_folder = Path(config.get('TEMP_FOLDER', 'storage/temp'))
        
        self.ensure_directories()
        
        self.max_file_size = config.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024)
        self.allowed_extensions = config.get('ALLOWED_EXTENSIONS', {
            'audio': {'wav', 'mp3', 'flac', 'm4a', 'ogg', 'webm'},
            'video': {'mp4', 'avi', 'mov', 'mkv', 'webm'}
        })
        
        self._start_cleanup_thread()
    
    def ensure_directories(self):
        directories = [
            self.upload_folder,
            self.output_folder,
            self.temp_folder
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory ensured: {directory}")
    
    def save_upload(self, file: FileStorage, file_id: str, original_filename: str) -> str:
        try:
            filename = secure_filename(original_filename)
            file_ext = Path(filename).suffix.lower()
            unique_filename = f"{file_id}_{filename}"
            save_path = self.upload_folder / unique_filename
            file.save(str(save_path))
            if not save_path.exists() or save_path.stat().st_size == 0:
                raise Exception("File was not saved properly")
            logger.info(f"File saved: {save_path}")
            return str(save_path)
        except Exception as e:
            logger.error(f"Failed to save upload: {e}")
            raise
    
    def create_temp_file(self, file_id: str, suffix: str = '.wav') -> str:
        try:
            temp_filename = f"{file_id}_temp_{int(time.time())}{suffix}"
            temp_path = self.temp_folder / temp_filename
            temp_path.touch()
            logger.info(f"Temp file created: {temp_path}")
            return str(temp_path)
        except Exception as e:
            logger.error(f"Failed to create temp file: {e}")
            raise
    
    def save_output(self, content: str, file_id: str, filename: str) -> str:
        try:
            output_filename = f"{file_id}_{secure_filename(filename)}"
            output_path = self.output_folder / output_filename
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Output saved: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to save output: {e}")
            raise
    
    def cleanup_temp_files(self, file_id: str):
        try:
            patterns = [
                f"{file_id}_*",
                f"*_{file_id}_*",
                f"*{file_id}*"
            ]
            cleaned_count = 0
            directories = [self.upload_folder, self.temp_folder, self.output_folder]
            for directory in directories:
                for pattern in patterns:
                    for file_path in directory.glob(pattern):
                        try:
                            if file_path.is_file():
                                file_path.unlink()
                                cleaned_count += 1
                                logger.debug(f"Cleaned up: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to clean up {file_path}: {e}")
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} files for ID: {file_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup temp files for {file_id}: {e}")
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            cutoff_timestamp = cutoff_time.timestamp()
            cleaned_count = 0
            directories = [self.upload_folder, self.temp_folder, self.output_folder]
            for directory in directories:
                if not directory.exists():
                    continue
                for file_path in directory.iterdir():
                    try:
                        if file_path.is_file():
                            file_mtime = file_path.stat().st_mtime
                            if file_mtime < cutoff_timestamp:
                                file_path.unlink()
                                cleaned_count += 1
                                logger.debug(f"Cleaned up old file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up {file_path}: {e}")
            logger.info(f"Cleaned up {cleaned_count} old files")
            return cleaned_count
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {e}")
            return 0
    
    def get_file_info(self, file_path: str) -> dict:
        try:
            path = Path(file_path)
            if not path.exists():
                return {'error': 'File not found'}
            stat = path.stat()
            return {
                'path': str(path),
                'name': path.name,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'extension': path.suffix.lower(),
                'exists': True
            }
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return {'error': str(e)}
    
    def is_valid_file_type(self, filename: str) -> bool:
        try:
            file_ext = Path(filename).suffix.lower().lstrip('.')
            all_extensions = set()
            for ext_list in self.allowed_extensions.values():
                all_extensions.update(ext_list)
            return file_ext in all_extensions
        except Exception:
            return False
    
    def get_file_category(self, filename: str) -> str:
        try:
            file_ext = Path(filename).suffix.lower().lstrip('.')
            for category, extensions in self.allowed_extensions.items():
                if file_ext in extensions:
                    return category
            return 'unknown'
        except Exception:
            return 'unknown'
    
    def copy_file(self, source: str, destination: str) -> bool:
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_path)
            logger.info(f"File copied: {source} -> {destination}")
            return True
        except Exception as e:
            logger.error(f"Failed to copy file {source} -> {destination}: {e}")
            return False
    
    def move_file(self, source: str, destination: str) -> bool:
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_path), str(dest_path))
            logger.info(f"File moved: {source} -> {destination}")
            return True
        except Exception as e:
            logger.error(f"Failed to move file {source} -> {destination}: {e}")
            return False
    
    def get_directory_size(self, directory: str) -> int:
        try:
            total_size = 0
            directory_path = Path(directory)
            if not directory_path.exists():
                return 0
            for file_path in directory_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except Exception as e:
            logger.error(f"Failed to get directory size for {directory}: {e}")
            return 0
    
    def get_storage_stats(self) -> dict:
        try:
            stats = {
                'upload_folder': {
                    'path': str(self.upload_folder),
                    'size': self.get_directory_size(self.upload_folder),
                    'file_count': len(list(self.upload_folder.glob('*'))) if self.upload_folder.exists() else 0
                },
                'output_folder': {
                    'path': str(self.output_folder),
                    'size': self.get_directory_size(self.output_folder),
                    'file_count': len(list(self.output_folder.glob('*'))) if self.output_folder.exists() else 0
                },
                'temp_folder': {
                    'path': str(self.temp_folder),
                    'size': self.get_directory_size(self.temp_folder),
                    'file_count': len(list(self.temp_folder.glob('*'))) if self.temp_folder.exists() else 0
                }
            }
            stats['total_size'] = sum(folder['size'] for folder in stats.values())
            stats['total_files'] = sum(folder['file_count'] for folder in stats.values())
            return stats
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {'error': str(e)}
    
    def _start_cleanup_thread(self):
        def cleanup_worker():
            while True:
                try:
                    time.sleep(3600)
                    self.cleanup_old_files(max_age_hours=24)
                except Exception as e:
                    logger.error(f"Cleanup thread error: {e}")
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("File cleanup thread started")
