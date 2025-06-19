"""
Job Management System for Async Operations
"""
import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class JobManager:
    """Simple file-based job management system"""
    
    def __init__(self, config):
        self.config = config
        self.jobs_dir = Path(config.get('UPLOAD_FOLDER', 'storage/uploads')).parent / 'jobs'
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_concurrent_jobs = config.get('MAX_CONCURRENT_JOBS', 5)
        self.job_timeout = config.get('JOB_TIMEOUT', 600)
        
        self.cleanup_interval = config.get('JOB_CLEANUP_INTERVAL', 3600)
        self._start_cleanup_thread()
    
    def create_job(self, job_id: str, job_data: Dict) -> bool:
        """Create a new job"""
        try:
            job_file = self.jobs_dir / f"{job_id}.json"
            
            job_data.update({
                'job_id': job_id,
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            })
            
            with open(job_file, 'w') as f:
                json.dump(job_data, f, indent=2)
            
            logger.info(f"Job {job_id} created")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create job {job_id}: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job by ID"""
        try:
            job_file = self.jobs_dir / f"{job_id}.json"
            
            if not job_file.exists():
                return None
            
            with open(job_file, 'r') as f:
                job_data = json.load(f)
            
            if self._is_job_timed_out(job_data):
                job_data['status'] = 'timeout'
                job_data['error'] = 'Job timed out'
                self.update_job_result(job_id, job_data)
            
            return job_data
            
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return None
    
    def update_job_status(self, job_id: str, status: str) -> bool:
        """Update job status"""
        try:
            job_data = self.get_job(job_id)
            if not job_data:
                return False
            
            job_data['status'] = status
            job_data['updated_at'] = datetime.now().isoformat()
            
            job_file = self.jobs_dir / f"{job_id}.json"
            with open(job_file, 'w') as f:
                json.dump(job_data, f, indent=2)
            
            logger.info(f"Job {job_id} status updated to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update job {job_id} status: {e}")
            return False
    
    def update_job_result(self, job_id: str, result: Dict) -> bool:
        """Update job with final result"""
        try:
            job_data = self.get_job(job_id)
            if not job_data:
                return False
            
            job_data.update(result)
            job_data['updated_at'] = datetime.now().isoformat()
            
            if job_data.get('status') in ['completed', 'failed', 'timeout']:
                job_data['completed_at'] = datetime.now().isoformat()
                
                if 'created_at' in job_data:
                    start_time = datetime.fromisoformat(job_data['created_at'])
                    end_time = datetime.now()
                    job_data['total_processing_time'] = (end_time - start_time).total_seconds()
            
            job_file = self.jobs_dir / f"{job_id}.json"
            with open(job_file, 'w') as f:
                json.dump(job_data, f, indent=2)
            
            logger.info(f"Job {job_id} result updated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update job {job_id} result: {e}")
            return False
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        try:
            job_data = self.get_job(job_id)
            if not job_data:
                return False
            
            if job_data['status'] not in ['pending', 'processing']:
                return False
            
            job_data['status'] = 'cancelled'
            job_data['cancelled_at'] = datetime.now().isoformat()
            job_data['updated_at'] = datetime.now().isoformat()
            
            job_file = self.jobs_dir / f"{job_id}.json"
            with open(job_file, 'w') as f:
                json.dump(job_data, f, indent=2)
            
            logger.info(f"Job {job_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
    
    def list_jobs(self, page: int = 1, per_page: int = 20, status: str = None) -> Dict:
        """List jobs with pagination"""
        try:
            job_files = list(self.jobs_dir.glob("*.json"))
            jobs = []
            
            for job_file in job_files:
                try:
                    with open(job_file, 'r') as f:
                        job_data = json.load(f)
                    
                    if status and job_data.get('status') != status:
                        continue
                    
                    jobs.append(job_data)
                    
                except Exception as e:
                    logger.warning(f"Failed to read job file {job_file}: {e}")
                    continue
            
            jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            total = len(jobs)
            start = (page - 1) * per_page
            end = start + per_page
            page_jobs = jobs[start:end]
            
            return {
                'jobs': page_jobs,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return {'jobs': [], 'pagination': {'page': 1, 'per_page': per_page, 'total': 0, 'pages': 0}}
    
    def get_stats(self) -> Dict:
        """Get job statistics"""
        try:
            job_files = list(self.jobs_dir.glob("*.json"))
            
            stats = {
                'total_jobs': 0,
                'by_status': {
                    'pending': 0,
                    'processing': 0,
                    'completed': 0,
                    'failed': 0,
                    'cancelled': 0,
                    'timeout': 0
                },
                'last_24h': 0,
                'avg_processing_time': 0,
                'total_processing_time': 0
            }
            
            processing_times = []
            now = datetime.now()
            
            for job_file in job_files:
                try:
                    with open(job_file, 'r') as f:
                        job_data = json.load(f)
                    
                    stats['total_jobs'] += 1
                    
                    status = job_data.get('status', 'unknown')
                    if status in stats['by_status']:
                        stats['by_status'][status] += 1
                    
                    created_at = job_data.get('created_at')
                    if created_at:
                        created_time = datetime.fromisoformat(created_at)
                        if now - created_time <= timedelta(hours=24):
                            stats['last_24h'] += 1
                    
                    proc_time = job_data.get('total_processing_time')
                    if proc_time:
                        processing_times.append(proc_time)
                        stats['total_processing_time'] += proc_time
                    
                except Exception as e:
                    logger.warning(f"Failed to read job file {job_file}: {e}")
                    continue
            
            if processing_times:
                stats['avg_processing_time'] = sum(processing_times) / len(processing_times)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get job stats: {e}")
            return {'error': str(e)}
    
    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed jobs"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            job_files = list(self.jobs_dir.glob("*.json"))
            cleaned_count = 0
            
            for job_file in job_files:
                try:
                    with open(job_file, 'r') as f:
                        job_data = json.load(f)
                    
                    if job_data.get('status') not in ['completed', 'failed', 'cancelled', 'timeout']:
                        continue
                    
                    completed_at = job_data.get('completed_at') or job_data.get('updated_at')
                    if completed_at:
                        completed_time = datetime.fromisoformat(completed_at)
                        if completed_time < cutoff_time:
                            job_file.unlink()
                            cleaned_count += 1
                            logger.info(f"Cleaned up old job: {job_file.stem}")
                    
                except Exception as e:
                    logger.warning(f"Failed to process job file {job_file}: {e}")
                    continue
            
            logger.info(f"Cleaned up {cleaned_count} old jobs")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")
            return 0
    
    def _is_job_timed_out(self, job_data: Dict) -> bool:
        """Check if job has timed out"""
        if job_data.get('status') not in ['pending', 'processing']:
            return False
        
        created_at = job_data.get('created_at')
        if not created_at:
            return False
        
        created_time = datetime.fromisoformat(created_at)
        elapsed = (datetime.now() - created_time).total_seconds()
        
        return elapsed > self.job_timeout
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(self.cleanup_interval)
                    self.cleanup_old_jobs()
                except Exception as e:
                    logger.error(f"Cleanup thread error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("Job cleanup thread started")
    
    def get_active_jobs_count(self) -> int:
        """Get count of active (pending/processing) jobs"""
        try:
            job_files = list(self.jobs_dir.glob("*.json"))
            active_count = 0
            
            for job_file in job_files:
                try:
                    with open(job_file, 'r') as f:
                        job_data = json.load(f)
                    
                    if job_data.get('status') in ['pending', 'processing']:
                        if not self._is_job_timed_out(job_data):
                            active_count += 1
                    
                except Exception:
                    continue
            
            return active_count
            
        except Exception as e:
            logger.error(f"Failed to get active jobs count: {e}")
            return 0
    
    def can_accept_new_job(self) -> bool:
        """Check if system can accept new jobs"""
        active_jobs = self.get_active_jobs_count()
        return active_jobs < self.max_concurrent_jobs
