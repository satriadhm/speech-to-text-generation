"""
Job Management API Routes
"""
from flask import Blueprint, jsonify, current_app
from utils.job_manager import JobManager

jobs_bp = Blueprint('jobs', __name__)

job_manager = None

@jobs_bp.before_app_first_request
def init_job_manager():
    global job_manager
    job_manager = JobManager(current_app.config)

@jobs_bp.route('/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get job status and results"""
    try:
        job = job_manager.get_job(job_id)
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify(job)
        
    except Exception as e:
        current_app.logger.error(f"Error getting job {job_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@jobs_bp.route('/jobs/<job_id>', methods=['DELETE'])
def cancel_job(job_id):
    """Cancel a pending job"""
    try:
        job = job_manager.get_job(job_id)
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        if job['status'] in ['completed', 'failed']:
            return jsonify({'error': 'Cannot cancel completed or failed job'}), 400
        
        success = job_manager.cancel_job(job_id)
        
        if success:
            return jsonify({'message': 'Job cancelled successfully'})
        else:
            return jsonify({'error': 'Failed to cancel job'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error cancelling job {job_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@jobs_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List all jobs (with pagination)"""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)  # Max 100 per page
        status = request.args.get('status')
        
        jobs = job_manager.list_jobs(page=page, per_page=per_page, status=status)
        
        return jsonify(jobs)
        
    except Exception as e:
        current_app.logger.error(f"Error listing jobs: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@jobs_bp.route('/jobs/stats', methods=['GET'])
def get_job_stats():
    """Get job statistics"""
    try:
        stats = job_manager.get_stats()
        return jsonify(stats)
        
    except Exception as e:
        current_app.logger.error(f"Error getting job stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500