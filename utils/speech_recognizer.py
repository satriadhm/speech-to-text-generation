"""
Speech Recognition Utilities
"""
import speech_recognition as sr
import logging
from typing import Dict, Optional, List
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    """Speech recognition handler with multiple engine support"""
    
    def __init__(self, config):
        self.config = config
        self.recognizer = sr.Recognizer()
        
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.operation_timeout = None
        self.recognizer.phrase_timeout = None
        self.recognizer.non_speaking_duration = 0.8
    
    def transcribe(self, audio_file_path: str, language: str = 'id-ID') -> Dict:
        """
        Transcribe audio file using multiple recognition engines
        """
        try:
            start_time = time.time()
            
            with sr.AudioFile(audio_file_path) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = self.recognizer.record(source)
            
            results = []
            
            google_result = self._recognize_with_google(audio_data, language)
            if google_result['success']:
                results.append(google_result)
            
            google_cloud_result = self._recognize_with_google_cloud(audio_data, language)
            if google_cloud_result['success']:
                results.append(google_cloud_result)
            
            wit_result = self._recognize_with_wit(audio_data, language)
            if wit_result['success']:
                results.append(wit_result)
            
            azure_result = self._recognize_with_azure(audio_data, language)
            if azure_result['success']:
                results.append(azure_result)
            
            if not results:
                return {
                    'success': False,
                    'error': 'All recognition engines failed',
                    'processing_time': time.time() - start_time
                }
            
            best_result = self._select_best_result(results)
            
            best_result.update({
                'language': language,
                'processing_time': time.time() - start_time,
                'engines_used': len(results),
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
    
    def _recognize_with_google(self, audio_data, language: str) -> Dict:
        """Recognize using Google Speech Recognition (free)"""
        try:
            text = self.recognizer.recognize_google(audio_data, language=language)
            return {
                'success': True,
                'text': text,
                'confidence': 0.8,
                'engine': 'google_free'
            }
        except sr.UnknownValueError:
            return {
                'success': False,
                'error': 'Google could not understand audio',
                'engine': 'google_free'
            }
        except sr.RequestError as e:
            return {
                'success': False,
                'error': f'Google service error: {e}',
                'engine': 'google_free'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Google recognition error: {e}',
                'engine': 'google_free'
            }
    
    def _recognize_with_google_cloud(self, audio_data, language: str) -> Dict:
        """Recognize using Google Cloud Speech API"""
        try:
            import os
            if not os.environ.get('GOOGLE_CLOUD_SPEECH_CREDENTIALS'):
                return {'success': False, 'error': 'Google Cloud credentials not available'}
            
            text = self.recognizer.recognize_google_cloud(
                audio_data, 
                credentials_json=os.environ.get('GOOGLE_CLOUD_SPEECH_CREDENTIALS'),
                language=language
            )
            return {
                'success': True,
                'text': text,
                'confidence': 0.9,
                'engine': 'google_cloud'
            }
        except sr.UnknownValueError:
            return {
                'success': False,
                'error': 'Google Cloud could not understand audio',
                'engine': 'google_cloud'
            }
        except sr.RequestError as e:
            return {
                'success': False,
                'error': f'Google Cloud service error: {e}',
                'engine': 'google_cloud'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Google Cloud recognition error: {e}',
                'engine': 'google_cloud'
            }
    
    def _recognize_with_wit(self, audio_data, language: str) -> Dict:
        """Recognize using Wit.ai"""
        try:
            import os
            wit_key = os.environ.get('WIT_AI_KEY')
            if not wit_key:
                return {'success': False, 'error': 'Wit.ai API key not available'}
            
            text = self.recognizer.recognize_wit(audio_data, key=wit_key)
            return {
                'success': True,
                'text': text,
                'confidence': 0.85,
                'engine': 'wit_ai'
            }
        except sr.UnknownValueError:
            return {
                'success': False,
                'error': 'Wit.ai could not understand audio',
                'engine': 'wit_ai'
            }
        except sr.RequestError as e:
            return {
                'success': False,
                'error': f'Wit.ai service error: {e}',
                'engine': 'wit_ai'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Wit.ai recognition error: {e}',
                'engine': 'wit_ai'
            }
    
    def _recognize_with_azure(self, audio_data, language: str) -> Dict:
        """Recognize using Azure Speech Services"""
        try:
            import os
            azure_key = os.environ.get('AZURE_SPEECH_KEY')
            azure_region = os.environ.get('AZURE_SPEECH_REGION')
            
            if not azure_key or not azure_region:
                return {'success': False, 'error': 'Azure Speech credentials not available'}
            
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
                'engine': 'azure'
            }
        except sr.UnknownValueError:
            return {
                'success': False,
                'error': 'Azure could not understand audio',
                'engine': 'azure'
            }
        except sr.RequestError as e:
            return {
                'success': False,
                'error': f'Azure service error: {e}',
                'engine': 'azure'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Azure recognition error: {e}',
                'engine': 'azure'
            }
    
    def _select_best_result(self, results: List[Dict]) -> Dict:
        """Select the best result from multiple recognition engines"""
        if not results:
            return None
        
        results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        best = results[0].copy()
        
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
        
        words_sets = [set(text.lower().split()) for text in texts]
        
        similarities = []
        for i in range(len(words_sets)):
            for j in range(i + 1, len(words_sets)):
                intersection = len(words_sets[i] & words_sets[j])
                union = len(words_sets[i] | words_sets[j])
                similarity = intersection / union if union > 0 else 0
                similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0
    
    def transcribe_with_timestamps(self, audio_file_path: str, language: str = 'id-ID') -> Dict:
        """
        Transcribe audio with word-level timestamps (requires specific engines)
        """
        basic_result = self.transcribe(audio_file_path, language)
        
        if basic_result['success']:
            words = basic_result['text'].split()
            estimated_duration = basic_result.get('processing_time', 1.0)
            time_per_word = estimated_duration / len(words) if words else 0
            
            word_timestamps = []
            for i, word in enumerate(words):
                word_timestamps.append({
                    'word': word,
                    'start_time': i * time_per_word,
                    'end_time': (i + 1) * time_per_word,
                    'confidence': basic_result.get('confidence', 0.8)
                })
            
            basic_result['word_timestamps'] = word_timestamps
        
        return basic_result
    
    def get_supported_languages(self) -> Dict:
        """Get list of supported languages for each engine"""
        return {
            'google_free': [
                'id-ID', 'en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE', 
                'it-IT', 'ja-JP', 'ko-KR', 'zh-CN', 'pt-BR', 'ru-RU'
            ],
            'google_cloud': [
                'id-ID', 'en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE',
                'it-IT', 'ja-JP', 'ko-KR', 'zh-CN', 'pt-BR', 'ru-RU',
                'ar-SA', 'hi-IN', 'th-TH', 'vi-VN', 'tr-TR', 'nl-NL'
            ],
            'wit_ai': ['en-US'],
            'azure': [
                'id-ID', 'en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE',
                'it-IT', 'ja-JP', 'ko-KR', 'zh-CN', 'pt-BR', 'ru-RU',
                'ar-SA', 'hi-IN', 'th-TH', 'vi-VN', 'tr-TR', 'nl-NL'
            ]
        }
    
    def validate_language_support(self, language: str) -> Dict:
        """Check which engines support the given language"""
        supported_engines = []
        all_engines = self.get_supported_languages()
        
        for engine, languages in all_engines.items():
            if language in languages:
                supported_engines.append(engine)
        
        return {
            'language': language,
            'supported': len(supported_engines) > 0,
            'engines': supported_engines,
            'primary_engine': supported_engines[0] if supported_engines else None
        }
