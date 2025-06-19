"""
Audio processing utilities for the Speech-to-Text API
"""
import subprocess
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import json
import wave
from pydub import AudioSegment
from pydub.utils import which
import librosa
import soundfile as sf
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Comprehensive audio processing and analysis"""
    
    def __init__(self, config):
        self.config = config
        self.sample_rate = config.get('AUDIO_SAMPLE_RATE', 16000)
        self.channels = config.get('AUDIO_CHANNELS', 1)
        self.output_format = config.get('AUDIO_FORMAT', 'wav')
        
        # Ensure FFmpeg is available
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """Check if FFmpeg is available"""
        ffmpeg_path = which("ffmpeg")
        if not ffmpeg_path:
            logger.warning("FFmpeg not found. Some audio conversions may fail.")
        else:
            logger.info(f"FFmpeg found at: {ffmpeg_path}")
    
    def get_audio_info(self, file_path: str) -> Dict:
        """Get comprehensive audio file information"""
        try:
            file_path = Path(file_path)
            
            # Basic file info
            info = {
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size,
                'file_extension': file_path.suffix.lower()
            }
            
            # Try to get audio info with pydub first
            try:
                audio = AudioSegment.from_file(str(file_path))
                info.update({
                    'duration_seconds': len(audio) / 1000.0,
                    'channels': audio.channels,
                    'sample_rate': audio.frame_rate,
                    'sample_width': audio.sample_width,
                    'frame_count': audio.frame_count(),
                    'bitrate': getattr(audio, 'bitrate', None)
                })
            except Exception as e:
                logger.warning(f"Pydub failed to read {file_path}: {e}")
                
                # Fallback to librosa
                try:
                    y, sr = librosa.load(str(file_path), sr=None)
                    info.update({
                        'duration_seconds': len(y) / sr,
                        'sample_rate': sr,
                        'frame_count': len(y),
                        'channels': 1 if y.ndim == 1 else y.shape[1]
                    })
                except Exception as e2:
                    logger.warning(f"Librosa failed to read {file_path}: {e2}")
                    
                    # Last resort: FFprobe
                    ffprobe_info = self._get_ffprobe_info(str(file_path))
                    if ffprobe_info:
                        info.update(ffprobe_info)
            
            # Add quality assessment
            info.update(self._assess_audio_quality(info))
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get audio info for {file_path}: {e}")
            return {'error': str(e)}
    
    def _get_ffprobe_info(self, file_path: str) -> Optional[Dict]:
        """Get audio info using FFprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return None
            
            data = json.loads(result.stdout)
            
            # Find audio stream
            audio_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                return None
            
            format_info = data.get('format', {})
            
            return {
                'duration_seconds': float(format_info.get('duration', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'bitrate': int(format_info.get('bit_rate', 0)),
                'codec': audio_stream.get('codec_name'),
                'format': format_info.get('format_name')
            }
            
        except Exception as e:
            logger.error(f"FFprobe failed: {e}")
            return None
    
    def _assess_audio_quality(self, info: Dict) -> Dict:
        """Assess audio quality for speech recognition"""
        quality_info = {
            'quality_score': 0,
            'quality_issues': [],
            'recommendations': []
        }
        
        # Check sample rate
        sample_rate = info.get('sample_rate', 0)
        if sample_rate >= 16000:
            quality_info['quality_score'] += 30
        elif sample_rate >= 8000:
            quality_info['quality_score'] += 20
            quality_info['quality_issues'].append('Low sample rate')
            quality_info['recommendations'].append('Use higher sample rate (>=16kHz) for better accuracy')
        else:
            quality_info['quality_issues'].append('Very low sample rate')
            quality_info['recommendations'].append('Sample rate too low for good speech recognition')
        
        # Check channels
        channels = info.get('channels', 0)
        if channels == 1:
            quality_info['quality_score'] += 20
        elif channels == 2:
            quality_info['quality_score'] += 15
            quality_info['recommendations'].append('Consider converting to mono for better processing')
        else:
            quality_info['quality_issues'].append('Unusual channel configuration')
        
        # Check duration
        duration = info.get('duration_seconds', 0)
        if 1 <= duration <= 300:  # 1 second to 5 minutes
            quality_info['quality_score'] += 20
        elif duration <= 600:  # up to 10 minutes
            quality_info['quality_score'] += 15
        elif duration > 600:
            quality_info['quality_issues'].append('Very long audio file')
            quality_info['recommendations'].append('Consider splitting long files for better processing')
        else:
            quality_info['quality_issues'].append('Very short audio file')
        
        # Check bitrate
        bitrate = info.get('bitrate', 0)
        if bitrate >= 128000:
            quality_info['quality_score'] += 15
        elif bitrate >= 64000:
            quality_info['quality_score'] += 10
        elif bitrate > 0:
            quality_info['quality_issues'].append('Low bitrate')
        
        # Check file size vs duration ratio
        file_size = info.get('file_size', 0)
        if duration > 0 and file_size > 0:
            size_per_second = file_size / duration
            if size_per_second >= 16000:  # roughly 128kbps
                quality_info['quality_score'] += 15
            elif size_per_second >= 8000:
                quality_info['quality_score'] += 10
        
        # Determine overall quality
        score = quality_info['quality_score']
        if score >= 90:
            quality_info['overall_quality'] = 'Excellent'
        elif score >= 70:
            quality_info['overall_quality'] = 'Good'
        elif score >= 50:
            quality_info['overall_quality'] = 'Fair'
        else:
            quality_info['overall_quality'] = 'Poor'
        
        return quality_info
    
    def convert_to_wav(self, input_path: str, output_path: str = None) -> Tuple[bool, str, Dict]:
        """Convert audio/video file to WAV format optimized for speech recognition"""
        try:
            input_path = Path(input_path)
            
            if output_path is None:
                output_path = input_path.parent / f"{input_path.stem}_converted.wav"
            else:
                output_path = Path(output_path)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            conversion_info = {
                'input_file': str(input_path),
                'output_file': str(output_path),
                'conversion_method': None,
                'start_time': datetime.now().isoformat()
            }
            
            # Method 1: Try FFmpeg (most reliable)
            if self._convert_with_ffmpeg(input_path, output_path):
                conversion_info['conversion_method'] = 'ffmpeg'
                conversion_info['success'] = True
            
            # Method 2: Try pydub as fallback
            elif self._convert_with_pydub(input_path, output_path):
                conversion_info['conversion_method'] = 'pydub'
                conversion_info['success'] = True
            
            # Method 3: Try librosa as last resort
            elif self._convert_with_librosa(input_path, output_path):
                conversion_info['conversion_method'] = 'librosa'
                conversion_info['success'] = True
            
            else:
                conversion_info['success'] = False
                conversion_info['error'] = 'All conversion methods failed'
                return False, str(output_path), conversion_info
            
            conversion_info['end_time'] = datetime.now().isoformat()
            
            # Verify output file
            if output_path.exists() and output_path.stat().st_size > 0:
                conversion_info['output_size'] = output_path.stat().st_size
                return True, str(output_path), conversion_info
            else:
                conversion_info['success'] = False
                conversion_info['error'] = 'Output file is empty or not created'
                return False, str(output_path), conversion_info
                
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return False, output_path or "", {'error': str(e)}
    
    def _convert_with_ffmpeg(self, input_path: Path, output_path: Path) -> bool:
        """Convert using FFmpeg"""
        try:
            cmd = [
                'ffmpeg', '-i', str(input_path),
                '-acodec', 'pcm_s16le',  # 16-bit PCM
                '-ar', str(self.sample_rate),  # Sample rate
                '-ac', str(self.channels),  # Mono
                '-af', 'volume=1.0',  # Normalize volume
                '-y',  # Overwrite output
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg conversion timed out")
            return False
        except Exception as e:
            logger.error(f"FFmpeg conversion failed: {e}")
            return False
    
    def _convert_with_pydub(self, input_path: Path, output_path: Path) -> bool:
        """Convert using pydub"""
        try:
            audio = AudioSegment.from_file(str(input_path))
            
            # Convert to target format
            audio = audio.set_frame_rate(self.sample_rate)
            audio = audio.set_channels(self.channels)
            audio = audio.set_sample_width(2)  # 16-bit
            
            # Export as WAV
            audio.export(str(output_path), format="wav")
            
            return True
            
        except Exception as e:
            logger.error(f"Pydub conversion failed: {e}")
            return False
    
    def _convert_with_librosa(self, input_path: Path, output_path: Path) -> bool:
        """Convert using librosa"""
        try:
            # Load audio
            y, sr = librosa.load(str(input_path), sr=self.sample_rate)
            
            # Convert to mono if needed
            if len(y.shape) > 1:
                y = librosa.to_mono(y)
            
            # Save as WAV
            sf.write(str(output_path), y, self.sample_rate)
            
            return True
            
        except Exception as e:
            logger.error(f"Librosa conversion failed: {e}")
            return False
    
    def enhance_audio_for_speech(self, input_path: str, output_path: str = None) -> Tuple[bool, str, Dict]:
        """Enhance audio quality specifically for speech recognition"""
        try:
            input_path = Path(input_path)
            
            if output_path is None:
                output_path = input_path.parent / f"{input_path.stem}_enhanced.wav"
            else:
                output_path = Path(output_path)
            
            enhancement_info = {
                'input_file': str(input_path),
                'output_file': str(output_path),
                'enhancements_applied': [],
                'start_time': datetime.now().isoformat()
            }
            
            # Load audio
            y, sr = librosa.load(str(input_path), sr=None)
            original_sr = sr
            
            # Resample to target sample rate if needed
            if sr != self.sample_rate:
                y = librosa.resample(y, orig_sr=sr, target_sr=self.sample_rate)
                sr = self.sample_rate
                enhancement_info['enhancements_applied'].append(f'Resampled from {original_sr}Hz to {sr}Hz')
            
            # Convert to mono if stereo
            if len(y.shape) > 1:
                y = librosa.to_mono(y)
                enhancement_info['enhancements_applied'].append('Converted to mono')
            
            # Noise reduction using spectral gating
            y_denoised = self._reduce_noise(y, sr)
            if not np.array_equal(y, y_denoised):
                y = y_denoised
                enhancement_info['enhancements_applied'].append('Noise reduction applied')
            
            # Normalize audio
            y_normalized = librosa.util.normalize(y)
            if not np.array_equal(y, y_normalized):
                y = y_normalized
                enhancement_info['enhancements_applied'].append('Audio normalized')
            
            # Apply high-pass filter to remove very low frequencies
            y_filtered = self._apply_highpass_filter(y, sr, cutoff=80)
            if not np.array_equal(y, y_filtered):
                y = y_filtered
                enhancement_info['enhancements_applied'].append('High-pass filter applied')
            
            # Save enhanced audio
            sf.write(str(output_path), y, sr)
            
            enhancement_info['end_time'] = datetime.now().isoformat()
            enhancement_info['success'] = True
            enhancement_info['output_size'] = output_path.stat().st_size
            
            return True, str(output_path), enhancement_info
            
        except Exception as e:
            logger.error(f"Audio enhancement failed: {e}")
            return False, output_path or "", {'error': str(e)}
    
    def _reduce_noise(self, y: np.ndarray, sr: int) -> np.ndarray:
        """Simple noise reduction using spectral gating"""
        try:
            # Compute short-time Fourier transform
            stft = librosa.stft(y)
            magnitude = np.abs(stft)
            
            # Estimate noise floor (bottom 10% of magnitude values)
            noise_floor = np.percentile(magnitude, 10)
            
            # Create mask: keep frequencies above noise threshold
            mask = magnitude > (noise_floor * 2)
            
            # Apply mask
            stft_denoised = stft * mask
            
            # Convert back to time domain
            y_denoised = librosa.istft(stft_denoised)
            
            return y_denoised
            
        except Exception:
            # Return original if denoising fails
            return y
    
    def _apply_highpass_filter(self, y: np.ndarray, sr: int, cutoff: float = 80) -> np.ndarray:
        """Apply high-pass filter to remove low frequencies"""
        try:
            from scipy import signal
            
            # Design high-pass filter
            nyquist = sr / 2
            normalized_cutoff = cutoff / nyquist
            
            if normalized_cutoff >= 1.0:
                return y
            
            b, a = signal.butter(5, normalized_cutoff, btype='high')
            
            # Apply filter
            y_filtered = signal.filtfilt(b, a, y)
            
            return y_filtered
            
        except Exception:
            # Return original if filtering fails
            return y
    
    def split_audio_by_silence(self, input_path: str, min_silence_len: int = 1000, 
                              silence_thresh: int = -40) -> List[Dict]:
        """Split audio file by silence for better processing of long files"""
        try:
            audio = AudioSegment.from_file(input_path)
            
            # Find silent segments
            from pydub.silence import split_on_silence
            
            chunks = split_on_silence(
                audio,
                min_silence_len=min_silence_len,  # minimum length of silence
                silence_thresh=silence_thresh,     # silence threshold
                keep_silence=500                   # keep some silence at edges
            )
            
            if len(chunks) <= 1:
                return [{'start': 0, 'end': len(audio), 'duration': len(audio) / 1000.0}]
            
            # Create segment information
            segments = []
            current_pos = 0
            
            for i, chunk in enumerate(chunks):
                segment = {
                    'segment_id': i,
                    'start': current_pos,
                    'end': current_pos + len(chunk),
                    'duration': len(chunk) / 1000.0,
                    'audio_data': chunk
                }
                segments.append(segment)
                current_pos += len(chunk)
            
            return segments
            
        except Exception as e:
            logger.error(f"Audio splitting failed: {e}")
            return []
    
    def validate_audio_for_speech_recognition(self, file_path: str) -> Dict:
        """Validate if audio file is suitable for speech recognition"""
        info = self.get_audio_info(file_path)
        
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # Check if we could read the file
        if 'error' in info:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Cannot read audio file: {info['error']}")
            return validation_result
        
        # Check duration
        duration = info.get('duration_seconds', 0)
        if duration == 0:
            validation_result['is_valid'] = False
            validation_result['errors'].append("Audio file appears to be empty")
        elif duration < 0.5:
            validation_result['warnings'].append("Audio file is very short")
        elif duration > 600:  # 10 minutes
            validation_result['warnings'].append("Audio file is very long, consider splitting")
        
        # Check sample rate
        sample_rate = info.get('sample_rate', 0)
        if sample_rate < 8000:
            validation_result['is_valid'] = False
            validation_result['errors'].append("Sample rate too low for speech recognition")
        elif sample_rate < 16000:
            validation_result['warnings'].append("Low sample rate may affect accuracy")
        
        # Check channels
        channels = info.get('channels', 0)
        if channels == 0:
            validation_result['is_valid'] = False
            validation_result['errors'].append("No audio channels detected")
        elif channels > 2:
            validation_result['warnings'].append("Multi-channel audio detected, will be converted to mono")
        
        # Add recommendations based on quality assessment
        quality_info = info.get('recommendations', [])
        validation_result['recommendations'].extend(quality_info)
        
        return validation_result


class AudioAnalyzer:
    """Advanced audio analysis for speech recognition optimization"""
    
    def __init__(self):
        pass
    
    def analyze_speech_content(self, file_path: str) -> Dict:
        """Analyze audio for speech characteristics"""
        try:
            y, sr = librosa.load(file_path, sr=None)
            
            analysis = {
                'has_speech': False,
                'speech_ratio': 0.0,
                'avg_volume': 0.0,
                'dynamic_range': 0.0,
                'zero_crossing_rate': 0.0,
                'spectral_centroid': 0.0,
                'mfcc_analysis': {}
            }
            
            analysis['has_speech'] = self._detect_speech_activity(y, sr)
            
            analysis['speech_ratio'] = self._calculate_speech_ratio(y, sr)
            
            analysis['avg_volume'] = float(np.mean(np.abs(y)))
            analysis['dynamic_range'] = float(np.max(y) - np.min(y))
            
            zcr = librosa.feature.zero_crossing_rate(y)
            analysis['zero_crossing_rate'] = float(np.mean(zcr))
            
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            analysis['spectral_centroid'] = float(np.mean(spectral_centroid))
            
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            analysis['mfcc_analysis'] = {
                'mfcc_mean': mfccs.mean(axis=1).tolist(),
                'mfcc_std': mfccs.std(axis=1).tolist()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Speech analysis failed: {e}")
            return {'error': str(e)}
    
    def _detect_speech_activity(self, y: np.ndarray, sr: int, frame_length: int = 2048) -> bool:
        """Simple voice activity detection"""
        try:
            hop_length = frame_length // 4
            energy = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            
            energy_threshold = np.percentile(energy, 70)
            
            active_frames = np.sum(energy > energy_threshold)
            total_frames = len(energy)
            
            return (active_frames / total_frames) > 0.1
            
        except Exception:
            return False
    
    def _calculate_speech_ratio(self, y: np.ndarray, sr: int) -> float:
        """Calculate ratio of speech to total audio"""
        try:
            frame_length = int(sr * 0.025) 
            hop_length = int(sr * 0.010)    
            
            energy = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            
            energy_threshold = np.percentile(energy, 30)
            
            speech_frames = np.sum(energy > energy_threshold)
            total_frames = len(energy)
            
            return float(speech_frames / total_frames) if total_frames > 0 else 0.0
            
        except Exception:
            return 0.0