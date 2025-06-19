"""
Admin API Routes
"""
from flask import Blueprint, jsonify, current_app, request
from datetime import datetime
import os
import psutil
import logging

from utils.job_manager import JobManager
from utils.file_manager import FileManager
from app.middleware.rate_limit import apply_rate_limit

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

job_manager = None
file_manager = None

@admin_bp.before_app_first_request
def init_admin_components():
    global job_manager, file_manager
    job_manager = JobManager(current_app.config)
    file_manager = FileManager(current_app.config)

@admin_bp.route('/stats', methods=['GET'])
@apply_rate_limit(limit=30, window=3600)
def get_system_stats():
    """Get comprehensive system statistics"""
    try:
        job_stats = job_manager.get_stats() if job_manager else {}
        
        storage_stats = file_manager.get_storage_stats() if file_manager else {}
        
        system_stats = get_system_info()
        
        api_stats = {
            'version': current_app.config.get('API_VERSION', '1.0.0'),
            'uptime': get_uptime(),
            'config': {
                'max_file_size': current_app.config.get('MAX_CONTENT_LENGTH', 0),
                'supported_languages': len(current_app.config.get('SUPPORTED_LANGUAGES', {})),
                'rate_limit_enabled': current_app.config.get('RATE_LIMIT_ENABLED', False),
                'max_concurrent_jobs': current_app.config.get('MAX_CONCURRENT_JOBS', 5)
            }
        }
        
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'jobs': job_stats,
            'storage': storage_stats,
            'system': system_stats,
            'api': api_stats
        })
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return jsonify({'error': 'Failed to get system statistics'}), 500

@admin_bp.route('/health', methods=['GET'])
def health_check():
    """Detailed health check"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': current_app.config.get('API_VERSION', '1.0.0'),
            'checks': {}
        }
        
        storage_stats = file_manager.get_storage_stats() if file_manager else {}
        disk_usage = psutil.disk_usage('/')
        disk_free_gb = disk_usage.free / (1024**3)
        
        health_status['checks']['disk_space'] = {
            'status': 'healthy' if disk_free_gb > 1 else 'warning',
            'free_gb': round(disk_free_gb, 2),
            'message': 'OK' if disk_free_gb > 1 else 'Low disk space'
        }
        
        memory = psutil.virtual_memory()
        memory_available_gb = memory.available / (1024**3)
        
        health_status['checks']['memory'] = {
            'status': 'healthy' if memory.percent < 80 else 'warning',
            'usage_percent': memory.percent,
            'available_gb': round(memory_available_gb, 2),
            'message': 'OK' if memory.percent < 80 else 'High memory usage'
        }
        
        # Check active jobs
        active_jobs = job_manager.get_active_jobs_count() if job_manager else 0
        max_jobs = current_app.config.get('MAX_CONCURRENT_JOBS', 5)
        
        health_status['checks']['jobs'] = {
            'status': 'healthy' if active_jobs < max_jobs else 'warning',
            'active_jobs': active_jobs,
            'max_jobs': max_jobs,
            'message': 'OK' if active_jobs < max_jobs else 'High job load'
        }
        
        # Overall status
        all_checks = [check['status'] for check in health_status['checks'].values()]
        if 'warning' in all_checks:
            health_status['status'] = 'warning'
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

@admin_bp.route('/cleanup', methods=['POST'])
@apply_rate_limit(limit=5, window=3600)
def manual_cleanup():
    """Manually trigger cleanup operations"""
    try:
        cleanup_results = {}
        
        data = request.get_json() or {}
        cleanup_files = data.get('cleanup_files', True)
        cleanup_jobs = data.get('cleanup_jobs', True)
        max_age_hours = data.get('max_age_hours', 24)
        
        if cleanup_files and file_manager:
            files_cleaned = file_manager.cleanup_old_files(max_age_hours)
            cleanup_results['files_cleaned'] = files_cleaned
        
        # Cleanup old jobs
        if cleanup_jobs and job_manager:
            jobs_cleaned = job_manager.cleanup_old_jobs(max_age_hours)
            cleanup_results['jobs_cleaned'] = jobs_cleaned
        
        cleanup_results.update({
            'timestamp': datetime.now().isoformat(),
            'max_age_hours': max_age_hours,
            'status': 'completed'
        })
        
        return jsonify(cleanup_results)
        
    except Exception as e:
        logger.error(f"Manual cleanup error: {e}")
        return jsonify({'error': 'Cleanup failed', 'details': str(e)}), 500

@admin_bp.route('/logs', methods=['GET'])
@apply_rate_limit(limit=10, window=3600)
def get_logs():
    """Get recent log entries"""
    try:
        lines = min(int(request.args.get('lines', 100)), 1000)
        level = request.args.get('level', 'INFO').upper()
        
        log_folder = current_app.config.get('LOG_FOLDER', 'storage/logs')
        log_file = os.path.join(log_folder, 'app.log')
        
        if not os.path.exists(log_file):
            return jsonify({'logs': [], 'message': 'Log file not found'})
        
        log_entries = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                for line in recent_lines:
                    if level == 'ALL' or level in line:
                        log_entries.append(line.strip())
        
        except Exception as e:
            return jsonify({'error': f'Failed to read log file: {e}'}), 500
        
        return jsonify({
            'logs': log_entries,
            'total_lines': len(log_entries),
            'level_filter': level,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'error': 'Failed to get logs'}), 500

@admin_bp.route('/config', methods=['GET'])
@apply_rate_limit(limit=20, window=3600)  # 20 requests per hour
def get_config():
    """Get current configuration (non-sensitive data only)"""
    try:
        safe_config = {
            'api_version': current_app.config.get('API_VERSION'),
            'max_file_size_mb': current_app.config.get('MAX_CONTENT_LENGTH', 0) // (1024 * 1024),
            'supported_languages': list(current_app.config.get('SUPPORTED_LANGUAGES', {}).keys()),
            'allowed_extensions': current_app.config.get('ALLOWED_EXTENSIONS', {}),
            'max_concurrent_jobs': current_app.config.get('MAX_CONCURRENT_JOBS'),
            'job_timeout': current_app.config.get('JOB_TIMEOUT'),
            'rate_limit_enabled': current_app.config.get('RATE_LIMIT_ENABLED'),
            'rate_limit_requests': current_app.config.get('RATE_LIMIT_REQUESTS'),
            'rate_limit_period': current_app.config.get('RATE_LIMIT_PERIOD'),
            'audio_settings': {
                'sample_rate': current_app.config.get('AUDIO_SAMPLE_RATE'),
                'channels': current_app.config.get('AUDIO_CHANNELS'),
                'format': current_app.config.get('AUDIO_FORMAT')
            }
        }
        
        return jsonify({
            'config': safe_config,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({'error': 'Failed to get configuration'}), 500

def get_system_info():
    """Get system information"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu': {
                'usage_percent': cpu_percent,
                'core_count': psutil.cpu_count()
            },
            'memory': {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'usage_percent': memory.percent
            },
            'disk': {
                'total_gb': round(disk.total / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'usage_percent': round((disk.used / disk.total) * 100, 2)
            },
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
        }
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return {'error': str(e)}

def get_uptime():
    """Get application uptime"""
    try:
        import time
        boot_time = psutil.boot_time()
        current_time = time.time()
        uptime_seconds = current_time - boot_time
        
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        return {
            'seconds': int(uptime_seconds),
            'human_readable': f"{days}d {hours}h {minutes}m"
        }
        
    except Exception:
        return {'error': 'Could not determine uptime'}