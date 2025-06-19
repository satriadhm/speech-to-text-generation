"""
History API Routes
"""
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timedelta
import logging

from utils.job_manager import JobManager
from utils.validator import validate_pagination_params
from app.middleware.rate_limit import apply_rate_limit

history_bp = Blueprint('history', __name__)
logger = logging.getLogger(__name__)

job_manager = None

@history_bp.before_app_first_request
def init_history_components():
    global job_manager
    job_manager = JobManager(current_app.config)

@history_bp.route('/history', methods=['GET'])
@apply_rate_limit(limit=60, window=3600)
def get_transcription_history():
    """Get transcription history with filtering and pagination"""
    try:
        page = request.args.get('page', '1')
        per_page = request.args.get('per_page', '20')
        
        pagination = validate_pagination_params(page, per_page)
        
        status = request.args.get('status')
        language = request.args.get('language')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        search = request.args.get('search')
        
        jobs_result = job_manager.list_jobs(
            page=pagination['page'], 
            per_page=pagination['per_page'],
            status=status
        )
        
        jobs = jobs_result.get('jobs', [])
        
        filtered_jobs = []
        for job in jobs:
            if language and job.get('language') != language:
                continue
            
            if date_from or date_to:
                job_date = job.get('created_at')
                if job_date:
                    try:
                        job_datetime = datetime.fromisoformat(job_date.replace('Z', '+00:00'))
                        
                        if date_from:
                            from_datetime = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                            if job_datetime < from_datetime:
                                continue
                        
                        if date_to:
                            to_datetime = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                            if job_datetime > to_datetime:
                                continue
                    except ValueError:
                        continue
            
            if search:
                transcription_text = ''
                if job.get('transcription') and job['transcription'].get('text'):
                    transcription_text = job['transcription']['text'].lower()
                
                if search.lower() not in transcription_text:
                    continue
            
            filtered_jobs.append(format_history_entry(job))
        
        total_filtered = len(filtered_jobs)
        start_idx = (pagination['page'] - 1) * pagination['per_page']
        end_idx = start_idx + pagination['per_page']
        page_jobs = filtered_jobs[start_idx:end_idx]
        
        return jsonify({
            'history': page_jobs,
            'pagination': {
                'page': pagination['page'],
                'per_page': pagination['per_page'],
                'total': total_filtered,
                'pages': (total_filtered + pagination['per_page'] - 1) // pagination['per_page']
            },
            'filters': {
                'status': status,
                'language': language,
                'date_from': date_from,
                'date_to': date_to,
                'search': search
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({'error': 'Failed to get transcription history'}), 500

@history_bp.route('/history/<job_id>', methods=['GET'])
@apply_rate_limit(limit=100, window=3600)
def get_history_detail(job_id):
    """Get detailed history for a specific transcription job"""
    try:
        job = job_manager.get_job(job_id)
        
        if not job:
            return jsonify({'error': 'Transcription not found'}), 404
        
        detail = format_history_detail(job)
        
        return jsonify(detail)
        
    except Exception as e:
        logger.error(f"Error getting history detail for {job_id}: {e}")
        return jsonify({'error': 'Failed to get transcription detail'}), 500

@history_bp.route('/history/<job_id>', methods=['DELETE'])
@apply_rate_limit(limit=20, window=3600)
def delete_history_entry(job_id):
    """Delete a history entry"""
    try:
        job = job_manager.get_job(job_id)
        
        if not job:
            return jsonify({'error': 'Transcription not found'}), 404
        
        if job.get('status') in ['pending', 'processing']:
            return jsonify({'error': 'Cannot delete active transcription job'}), 400
        
        success = job_manager.cancel_job(job_id)
        
        if success:
            return jsonify({'message': 'History entry deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete history entry'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting history entry {job_id}: {e}")
        return jsonify({'error': 'Failed to delete history entry'}), 500

@history_bp.route('/history/stats', methods=['GET'])
@apply_rate_limit(limit=30, window=3600)
def get_history_stats():
    """Get transcription history statistics"""
    try:
        job_stats = job_manager.get_stats()
        
        all_jobs = job_manager.list_jobs(page=1, per_page=1000)
        jobs = all_jobs.get('jobs', [])
        
        stats = {
            'total_transcriptions': job_stats.get('total_jobs', 0),
            'status_breakdown': job_stats.get('by_status', {}),
            'recent_activity': {
                'last_24h': job_stats.get('last_24h', 0),
                'last_7d': count_jobs_in_period(jobs, days=7),
                'last_30d': count_jobs_in_period(jobs, days=30)
            },
            'performance': {
                'avg_processing_time_seconds': job_stats.get('avg_processing_time', 0),
                'total_processing_time_seconds': job_stats.get('total_processing_time', 0)
            },
            'language_breakdown': get_language_breakdown(jobs),
            'success_rate': calculate_success_rate(job_stats.get('by_status', {})),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting history stats: {e}")
        return jsonify({'error': 'Failed to get history statistics'}), 500

def format_history_entry(job):
    """Format job data for history list"""
    return {
        'job_id': job.get('job_id'),
        'status': job.get('status'),
        'language': job.get('language'),
        'created_at': job.get('created_at'),
        'completed_at': job.get('completed_at'),
        'file_info': {
            'filename': job.get('file_info', {}).get('filename'),
            'size': job.get('file_info', {}).get('size')
        },
        'transcription_preview': get_transcription_preview(job),
        'processing_time': job.get('total_processing_time'),
        'error': job.get('error') if job.get('status') == 'failed' else None
    }

def format_history_detail(job):
    """Format job data for detailed view"""
    detail = {
        'job_id': job.get('job_id'),
        'status': job.get('status'),
        'language': job.get('language'),
        'created_at': job.get('created_at'),
        'updated_at': job.get('updated_at'),
        'completed_at': job.get('completed_at'),
        'file_info': job.get('file_info', {}),
        'transcription': job.get('transcription', {}),
        'audio_info': job.get('audio_info', {}),
        'processing_info': job.get('processing_info', {}),
        'performance': {
            'processing_time': job.get('processing_time'),
            'total_processing_time': job.get('total_processing_time')
        },
        'warnings': job.get('warnings', []),
        'error': job.get('error'),
        'callback_url': job.get('callback_url')
    }
    
    return detail

def get_transcription_preview(job, max_length=100):
    """Get a preview of the transcription text"""
    transcription = job.get('transcription', {})
    
    if transcription.get('success') and transcription.get('text'):
        text = transcription['text']
        if len(text) > max_length:
            return text[:max_length] + '...'
        return text
    
    return None

def count_jobs_in_period(jobs, days):
    """Count jobs created in the last N days"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        count = 0
        
        for job in jobs:
            created_at = job.get('created_at')
            if created_at:
                try:
                    created_datetime = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if created_datetime >= cutoff_date:
                        count += 1
                except ValueError:
                    continue
        
        return count
    except Exception:
        return 0

def get_language_breakdown(jobs):
    """Get breakdown of jobs by language"""
    try:
        language_count = {}
        
        for job in jobs:
            language = job.get('language', 'unknown')
            language_count[language] = language_count.get(language, 0) + 1
        
        return language_count
    except Exception:
        return {}

def calculate_success_rate(status_breakdown):
    """Calculate success rate from status breakdown"""
    try:
        total = sum(status_breakdown.values())
        if total == 0:
            return 0
        
        completed = status_breakdown.get('completed', 0)
        return round((completed / total) * 100, 2)
    except Exception:
        return 0
