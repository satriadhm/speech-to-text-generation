"""
Speech Recognition Utilities (Free Tier Only)
"""
import speech_recognition as sr
import logging
from typing import Dict, Optional, List
from datetime import datetime
import time
import os

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    """Speech recognition handler with free tier engines"""
    
    def __init__(self, config):
        self.config = config
        self.recognizer = sr.Recognizer()
        
        # Configure recognizer settings for better performance
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.operation_timeout = None
        self.recognizer.phrase_timeout = None
        self.recognizer.non_speaking_duration = 0.8
    
    def transcribe(self, audio_file_path: str, language: str = 'id-ID') -> Dict:
        """
        Transcribe audio file using free tier recognition engines
        """
        try:
            start_time = time.time()
            
            # Load audio file
            with sr.AudioFile(audio_file_path) as source:
                # Adjust for ambient noise (helps with accuracy)
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                # Record the audio
                audio_data = self.recognizer.record(source)
            
            # Try multiple recognition engines in order of preference
            results = []
            
            # 1. Google Speech Recognition (free tier) - Most reliable
            google_result = self._recognize_with_google_free(audio_data, language)
            if google_result['success']:
                results.append(google_result)
            
            # 2. Try Google Cloud if credentials are available (has free quota)
            if os.environ.get('GOOGLE_CLOUD_SPEECH_CREDENTIALS'):
                google_cloud_result = self._recognize_with_google_cloud(audio_data, language)
                if google_cloud_result['success']:
                    results.append(google_cloud_result)
            
            # 3. Try Azure if credentials are available (has free quota)
            if os.environ.get('AZURE_SPEECH_KEY') and os.environ.get('AZURE_SPEECH_REGION'):
                azure_result = self._recognize_with_azure(audio_data, language)
                if azure_result['success']:
                    results.append(azure_result)
            
            # 4. Try Wit.ai if API key is available (free for limited use)
            if os.environ.get('WIT_AI_KEY') and language.startswith('en'):
                wit_result = self._recognize_with_wit(audio_data, language)
                if wit_result['success']:
                    results.append(wit_result)
            
            # If no results, return error
            if not results:
                return {
                    'success': False,
                    'error': 'All recognition engines failed',
                    'processing_time': time.time() - start_time,
                    'engines_tried': ['google_free']
                }
            
            # Select best result
            best_result = self._select_best_result(results)
            
            # Add metadata
            best_result.update({
                'language': language,
                'processing_time': time.time() - start_time,
                'engines_used': len(results),
                'engines_tried': [r['engine'] for r in results],
                'alternative_results': [r for r in results if r != best_result][:2]
            })
            
            return best_result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time if 'start_time' in locals() else 0
            }
    
    def _recognize_with_google_free(self, audio_data, language: str) -> Dict:
        """Recognize using Google Speech Recognition (free tier)"""
        try:
            text = self.recognizer.recognize_google(audio_data, language=language)
            return {
                'success': True,
                'text': text,
                'confidence': 0.8,  # Google free doesn't provide confidence scores
                'engine': 'google_free',
                'cost': 'free'
            }
        except sr.UnknownValueError:
            return {
                'success': False,
                'error': 'Google could not understand the audio',
                'engine': 'google_free'
            }
        except sr.RequestError as e:
            logger.error(f"Google service error: {e}")
            return {
                'success': False,
                'error': f'Google service error: {e}',
                'engine': 'google_free'
            }
        except Exception as e:
            logger.error(f"Google recognition error: {e}")
            return {
                'success': False,
                'error': f'Google recognition error: {e}',
                'engine': 'google_free'
            }
    
    def _recognize_with_google_cloud(self, audio_data, language: str) -> Dict:
        """Recognize using Google Cloud Speech API (if credentials available)"""
        try:
            credentials_path = os.environ.get('GOOGLE_CLOUD_SPEECH_CREDENTIALS')
            if not credentials_path or not os.path.exists(credentials_path):
                return {'success': False, 'error': 'Google Cloud credentials not found'}
            
            # Read credentials file
            with open(credentials_path, 'r') as f:
                credentials_json = f.read()
            
            text = self.recognizer.recognize_google_cloud(
                audio_data, 
                credentials_json=credentials_json,
                language=language
            )
            return {
                'success': True,
                'text': text,
                'confidence': 0.9,  # Assume high confidence for Google Cloud
                'engine': 'google_cloud',
                'cost': 'free_quota'
            }
        except sr.UnknownValueError:
            return {
                'success': False,
                'error': 'Google Cloud could not understand the audio',
                'engine': 'google_cloud'
            }
        except sr.RequestError as e:
            logger.error(f"Google Cloud service error: {e}")
            return {
                'success': False,
                'error': f'Google Cloud service error: {e}',
                'engine': 'google_cloud'
            }
        except Exception as e:
            logger.error(f"Google Cloud recognition error: {e}")
            return {
                'success': False,
                'error': f'Google Cloud recognition error: {e}',
                'engine': 'google_cloud'
            }
    
    def _recognize_with_azure(self, audio_data, language: str) -> Dict:
        """Recognize using Azure Speech Services (if credentials available)"""
        try:
            azure_key = os.environ.get('AZURE_SPEECH_KEY')
            azure_region = os.environ.get('AZURE_SPEECH_REGION')
            
            if not azure_key or not azure_region:
                return {'success': False, 'error': 'Azure Speech credentials not configured'}
            
            text = self.recognizer.recognize_azure(
                audio_data, 
                key=azure_key, 
                location=azure_region,
                language=language
            )
            return {
                'success': True,
                'text': text,
                'confidence': 0.9,
                'engine': 'azure',
                'cost': 'free_quota'
            }
        except sr.UnknownValueError:
            return {
                'success': False,
                'error': 'Azure could not understand the audio',
                'engine': 'azure'
            }
        except sr.RequestError as e:
            logger.error(f"Azure service error: {e}")
            return {
                'success': False,
                'error': f'Azure service error: {e}',
                'engine': 'azure'
            }
        except Exception as e:
            logger.error(f"Azure recognition error: {e}")
            return {
                'success': False,
                'error': f'Azure recognition error: {e}',
                'engine': 'azure'
            }
    
    def _recognize_with_wit(self, audio_data, language: str) -> Dict:
        """Recognize using Wit.ai (if API key available, English only)"""
        try:
            wit_key = os.environ.get('WIT_AI_KEY')
            if not wit_key:
                return {'success': False, 'error': 'Wit.ai API key not configured'}
            
            # Wit.ai primarily supports English
            if not language.startswith('en'):
                return {'success': False, 'error': 'Wit.ai only supports English languages'}
            
            text = self.recognizer.recognize_wit(audio_data, key=wit_key)
            return {
                'success': True,
                'text': text,
                'confidence': 0.85,
                'engine': 'wit_ai',
                'cost': 'free'
            }
        except sr.UnknownValueError:
            return {
                'success': False,
                'error': 'Wit.ai could not understand the audio',
                'engine': 'wit_ai'
            }
        except sr.RequestError as e:
            logger.error(f"Wit.ai service error: {e}")
            return {
                'success': False,
                'error': f'Wit.ai service error: {e}',
                'engine': 'wit_ai'
            }
        except Exception as e:
            logger.error(f"Wit.ai recognition error: {e}")
            return {
                'success': False,
                'error': f'Wit.ai recognition error: {e}',
                'engine': 'wit_ai'
            }
    
    def _select_best_result(self, results: List[Dict]) -> Dict:
        """Select the best result from multiple recognition engines"""
        if not results:
            return None
        
        # Sort by confidence (highest first)
        results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Return the result with highest confidence
        best = results[0].copy()
        
        # Add consensus information if multiple results
        if len(results) > 1:
            texts = [r['text'] for r in results]
            best['consensus'] = {
                'total_engines': len(results),
                'all_texts': texts,
                'text_similarity': self._calculate_text_similarity(texts)
            }
        
        return best
    
    def _calculate_text_similarity(self, texts: List[str]) -> float:
        """Calculate similarity between multiple text results"""
        if len(texts) < 2:
            return 1.0
        
        # Simple similarity calculation based on word overlap
        words_sets = [set(text.lower().split()) for text in texts]
        
        # Calculate average pairwise similarity
        similarities = []
        for i in range(len(words_sets)):
            for j in range(i + 1, len(words_sets)):
                intersection = len(words_sets[i] & words_sets[j])
                union = len(words_sets[i] | words_sets[j])
                similarity = intersection / union if union > 0 else 0
                similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0
    
    def get_available_engines(self) -> Dict:
        """Get list of available recognition engines"""
        engines = {
            'google_free': {
                'available': True,
                'cost': 'free',
                'description': 'Google Speech Recognition (free tier)',
                'languages': ['id-ID', 'en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE', 
                             'it-IT', 'ja-JP', 'ko-KR', 'zh-CN', 'pt-BR', 'ru-RU']
            }
        }
        
        # Check Google Cloud availability
        if os.environ.get('GOOGLE_CLOUD_SPEECH_CREDENTIALS'):
            engines['google_cloud'] = {
                'available': True,
                'cost': 'free_quota_then_paid',
                'description': 'Google Cloud Speech API',
                'languages': ['id-ID', 'en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE',
                             'it-IT', 'ja-JP', 'ko-KR', 'zh-CN', 'pt-BR', 'ru-RU',
                             'ar-SA', 'hi-IN', 'th-TH', 'vi-VN', 'tr-TR', 'nl-NL']
            }
        
        # Check Azure availability
        if os.environ.get('AZURE_SPEECH_KEY') and os.environ.get('AZURE_SPEECH_REGION'):
            engines['azure'] = {
                'available': True,
                'cost': 'free_quota_then_paid',
                'description': 'Azure Speech Services',
                'languages': ['id-ID', 'en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE',
                             'it-IT', 'ja-JP', 'ko-KR', 'zh-CN', 'pt-BR', 'ru-RU',
                             'ar-SA', 'hi-IN', 'th-TH', 'vi-VN', 'tr-TR', 'nl-NL']
            }
        
        # Check Wit.ai availability
        if os.environ.get('WIT_AI_KEY'):
            engines['wit_ai'] = {
                'available': True,
                'cost': 'free',
                'description': 'Wit.ai (English only)',
                'languages': ['en-US', 'en-GB']
            }
        
        return engines
    
    def validate_language_support(self, language: str) -> Dict:
        """Check which engines support the given language"""
        available_engines = self.get_available_engines()
        supported_engines = []
        
        for engine_name, engine_info in available_engines.items():
            if engine_info['available'] and language in engine_info['languages']:
                supported_engines.append(engine_name)
        
        return {
            'language': language,
            'supported': len(supported_engines) > 0,
            'engines': supported_engines,
            'primary_engine': supported_engines[0] if supported_engines else None,
            'fallback_engines': supported_engines[1:] if len(supported_engines) > 1 else []
        }
    
    def get_engine_status(self) -> Dict:
        """Get status of all speech recognition engines"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'engines': {}
        }
        
        # Test Google free (always available)
        status['engines']['google_free'] = {
            'available': True,
            'status': 'ready',
            'cost': 'free',
            'message': 'Google Speech Recognition (free tier) is available'
        }
        
        # Test Google Cloud
        if os.environ.get('GOOGLE_CLOUD_SPEECH_CREDENTIALS'):
            try:
                creds_path = os.environ