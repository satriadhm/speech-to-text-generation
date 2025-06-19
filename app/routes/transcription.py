"""
Transcription API Routes
"""
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
import threading
import time

from utils.audio_processor import AudioProcessor
from utils.speech_recognizer import SpeechRecognizer
from utils.file_manager import FileManager
from utils.job_manager import JobManager
from utils.validator import validate_file, validate_language

transcription_bp = Blueprint('transcription', __name__)

audio_processor = None
speech_recognizer = None
file_manager = None
job_manager = None

@transcription_bp.before_app_first_request
def init_components():
    global audio_processor, speech_recognizer, file_manager, job_manager
    audio_processor = AudioProcessor(current_app.config)
    speech_recognizer = SpeechRecognizer(current_app.config)
    file_manager = FileManager(current_app.config)
    job_manager = JobManager(current_app.config)

@transcription_bp.route('/transcribe', methods=['POST'])
def transcribe_sync():
    """Synchronous transcription endpoint"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file
        validation_result = validate_file(file, current_app.config)
        if not validation_result['valid']:
            return jsonify({'error': validation_result['message']}), 400
        
        language = request.form.get('language', current_app.config['DEFAULT_LANGUAGE'])
        enhance_audio = request.form.get('enhance_audio', 'false').lower() == 'true'
        
        if not validate_language(language, current_app.config):
            return jsonify({'error': f'Unsupported language: {language}'}), 400
        
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        upload_path = file_manager.save_upload(file, file_id, filename)
        
        try:
            audio_info = audio_processor.get_audio_info(upload_path)
            
            validation = audio_processor.validate_audio_for_speech_recognition(upload_path)
            if not validation['is_valid']:
                return jsonify({
                    'error': 'Audio file not suitable for speech recognition',
                    'details': validation['errors']
                }), 400
            
            if not upload_path.endswith('.wav'):
                success, wav_path, conversion_info = audio_processor.convert_to_wav(upload_path)
                if not success:
                    return jsonify({
                        'error': 'Failed to convert audio file',
                        'details': conversion_info
                    }), 500
                processed_path = wav_path
            else:
                processed_path = upload_path
                conversion_info = {'conversion_method': 'none'}
            
            if enhance_audio:
                success, enhanced_path, enhancement_info = audio_processor.enhance_audio_for_speech(processed_path)
                if success:
                    processed_path = enhanced_path
                else:
                    current_app.logger.warning(f"Audio enhancement failed: {enhancement_info}")
            
            transcription_result = speech_recognizer.transcribe(processed_path, language)
            
            response = {
                'transcription': transcription_result,
                'audio_info': audio_info,
                'processing_info': {
                    'language': language,
                    'enhanced': enhance_audio,
                    'conversion': conversion_info,
                    'file_id': file_id,
                    'processed_at': datetime.now().isoformat()
                }
            }
            
            if validation.get('warnings'):
                response['warnings'] = validation['warnings']
            
            return jsonify(response)
            
        finally:
            file_manager.cleanup_temp_files(file_id)
            
    except Exception as e:
        current_app.logger.error(f"Transcription error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@transcription_bp.route('/transcribe/async', methods=['POST'])
def transcribe_async():
    """Asynchronous transcription endpoint"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        validation_result = validate_file(file, current_app.config)
        if not validation_result['valid']:
            return jsonify({'error': validation_result['message']}), 400
        
        language = request.form.get('language', current_app.config['DEFAULT_LANGUAGE'])
        enhance_audio = request.form.get('enhance_audio', 'false').lower() == 'true'
        callback_url = request.form.get('callback_url')
        
        if not validate_language(language, current_app.config):
            return jsonify({'error': f'Unsupported language: {language}'}), 400
        
        job_id = str(uuid.uuid4())
        job_data = {
            'job_id': job_id,
            'status': 'pending',
            'language': language,
            'enhance_audio': enhance_audio,
            'callback_url': callback_url,
            'created_at': datetime.now().isoformat(),
            'file_info': {
                'filename': secure_filename(file.filename),
                'size': len(file.read())
            }
        }
        
        file.seek(0)
        
        job_manager.create_job(job_id, job_data)
        
        filename = secure_filename(file.filename)
        upload_path = file_manager.save_upload(file, job_id, filename)
        
        thread = threading.Thread(
            target=process_async_transcription,
            args=(job_id, upload_path, language, enhance_audio, callback_url)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'status': 'pending',
            'message': 'Transcription job started',
            'status_url': f'/api/v1/jobs/{job_id}'
        }), 202
        
    except Exception as e:
        current_app.logger.error(f"Async transcription error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def process_async_transcription(job_id, file_path, language, enhance_audio, callback_url):
    """Background task for async transcription"""
    try:
        with current_app.app_context():
            job_manager.update_job_status(job_id, 'processing')
            
            global audio_processor, speech_recognizer, file_manager
            if not audio_processor:
                audio_processor = AudioProcessor(current_app.config)
                speech_recognizer = SpeechRecognizer(current_app.config)
                file_manager = FileManager(current_app.config)
            
            audio_info = audio_processor.get_audio_info(file_path)
            
            validation = audio_processor.validate_audio_for_speech_recognition(file_path)
            if not validation['is_valid']:
                job_manager.update_job_result(job_id, {
                    'status': 'failed',
                    'error': 'Audio file not suitable for speech recognition',
                    'details': validation['errors']
                })
                return
            
            processed_path = file_path
            conversion_info = {'conversion_method': 'none'}
            
            if not file_path.endswith('.wav'):
                success, wav_path, conversion_info = audio_processor.convert_to_wav(file_path)
                if not success:
                    job_manager.update_job_result(job_id, {
                        'status': 'failed',
                        'error': 'Failed to convert audio file',
                        'details': conversion_info
                    })
                    return
                processed_path = wav_path
            
            enhancement_info = None
            if enhance_audio:
                success, enhanced_path, enhancement_info = audio_processor.enhance_audio_for_speech(processed_path)
                if success:
                    processed_path = enhanced_path
            
            transcription_result = speech_recognizer.transcribe(processed_path, language)
            
            result = {
                'status': 'completed',
                'transcription': transcription_result,
                'audio_info': audio_info,
                'processing_info': {
                    'language': language,
                    'enhanced': enhance_audio,
                    'conversion': conversion_info,
                    'enhancement': enhancement_info,
                    'completed_at': datetime.now().isoformat()
                }
            }
            
            if validation.get('warnings'):
                result['warnings'] = validation['warnings']
            
            job_manager.update_job_result(job_id, result)
            
            if callback_url:
                send_callback(callback_url, job_id, result)
            
    except Exception as e:
        current_app.logger.error(f"Async processing error for job {job_id}: {e}")
        job_manager.update_job_result(job_id, {
            'status': 'failed',
            'error': str(e),
            'failed_at': datetime.now().isoformat()
        })
    finally:
        file_manager.cleanup_temp_files(job_id)

def send_callback(callback_url, job_id, result):
    """Send callback notification"""
    try:
        import requests
        
        payload = {
            'job_id': job_id,
            'result': result
        }
        
        response = requests.post(
            callback_url,
            json=payload,
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            current_app.logger.info(f"Callback sent successfully for job {job_id}")
        else:
            current_app.logger.warning(f"Callback failed for job {job_id}: {response.status_code}")
            
    except Exception as e:
        current_app.logger.error(f"Callback error for job {job_id}: {e}")

@transcription_bp.route('/languages', methods=['GET'])
def get_supported_languages():
    """Get list of supported languages"""
    return jsonify({
        'languages': current_app.config['SUPPORTED_LANGUAGES'],
        'default': current_app.config['DEFAULT_LANGUAGE']
    })

@transcription_bp.route('/info', methods=['GET'])
def get_api_info():
    """Get API information and capabilities"""
    return jsonify({
        'api_version': current_app.config['API_VERSION'],
        'supported_formats': {
            'audio': list(current_app.config['ALLOWED_EXTENSIONS']['audio']),
            'video': list(current_app.config['ALLOWED_EXTENSIONS']['video'])
        },
        'max_file_size': current_app.config['MAX_CONTENT_LENGTH'],
        'supported_languages': len(current_app.config['SUPPORTED_LANGUAGES']),
        'features': {
            'sync_transcription': True,
            'async_transcription': True,
            'audio_enhancement': True,
            'multi_language': True,
            'callback_support': True
        }
    })