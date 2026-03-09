import whisper
import torch
import pyttsx3
import threading
import os
import shutil
import numpy as np
import scipy.io.wavfile as wavfile
import subprocess
import tempfile
import aifc
import contextlib
from config import Config
from googletrans import Translator as GoogleTranslator

class SpeechTranslator:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SpeechTranslator, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        print(" Initializing Speech Translator...")
        
        # Load Whisper model onto GPU if available, else CPU
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.whisper_model = whisper.load_model(Config.WHISPER_MODEL, device=device)
        print(f" Whisper model '{Config.WHISPER_MODEL}' loaded")
        
        # Initialize Google Translator (fast, no model download needed)
        self.google_translator = GoogleTranslator()
        print(" Google Translator initialized")
        
        # No local transformers-based translation pipeline; use Google Translate
        # (googletrans) for translation requests.
        
        # TTS engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)
        self.tts_engine.setProperty('volume', 0.9)

        # ffmpeg availability (Whisper and many conversions require ffmpeg)
        self.ffmpeg_path = shutil.which('ffmpeg')
        self.ffmpeg_available = bool(self.ffmpeg_path)
        if not self.ffmpeg_available:
            print(" ffmpeg not found in PATH — audio conversion/transcription may fail. Install ffmpeg (e.g. `brew install ffmpeg`).")
        
        self._initialized = True
        print(" Speech Translator initialized successfully")

    def _convert_to_wav16(self, src_path):

        # Read header bytes to detect container
        try:
            with open(src_path, 'rb') as fh:
                header = fh.read(12)
        except Exception as e:
            raise

        # If RIFF (WAV), try to ensure int16 format
        if header.startswith(b'RIFF'):
            try:
                rate, data = wavfile.read(src_path)
                if data.dtype == np.int16:
                    return src_path
                tmpfd, tmp_path = tempfile.mkstemp(suffix='.wav')
                os.close(tmpfd)
                if data.dtype.kind == 'f':
                    max_val = np.max(np.abs(data))
                    scaled = (data / max_val) * 0.9 if max_val > 0 else data
                    int_data = (scaled * 32767).astype(np.int16)
                else:
                    int_data = data.astype(np.int16)
                wavfile.write(tmp_path, rate, int_data)
                return tmp_path
            except Exception:
                pass

        # If AIFF (FORM) use aifc to convert
        encountered_aiff = False
        if header.startswith(b'FORM'):
            encountered_aiff = True
            try:
                with contextlib.closing(aifc.open(src_path, 'r')) as af:
                    nframes = af.getnframes()
                    sample_rate = af.getframerate()
                    sampwidth = af.getsampwidth()
                    nchannels = af.getnchannels()
                    raw = af.readframes(nframes)

                    if sampwidth == 1:
                        dtype = np.uint8
                    elif sampwidth == 2:
                        dtype = np.int16
                    elif sampwidth == 4:
                        dtype = np.int32
                    else:
                        dtype = np.int16

                    data = np.frombuffer(raw, dtype=dtype)

                    # If multiple channels, reshape interleaved PCM into (n_samples, n_channels)
                    if nchannels > 1 and data.size % nchannels == 0:
                        data = data.reshape(-1, nchannels)

                    # Normalize/convert to int16 PCM
                    if data.dtype != np.int16:
                        try:
                            fdata = data.astype(np.float32)
                            max_val = np.max(np.abs(fdata)) if fdata.size > 0 else 0.0
                            if max_val > 0:
                                scaled = (fdata / max_val) * 0.9
                            else:
                                scaled = fdata
                            int_data = (scaled * 32767).astype(np.int16)
                        except Exception:
                            int_data = data.astype(np.int16)
                    else:
                        int_data = data

                    tmpfd, tmp_path = tempfile.mkstemp(suffix='.wav')
                    os.close(tmpfd)
                    wavfile.write(tmp_path, sample_rate, int_data)
                    return tmp_path
            except Exception as e:
                # aifc can fail for compressed/encoded AIFF files (common on some macOS outputs)
                print(f"AIFF->WAV conversion failed (aifc): {e}")

                # Try reading with soundfile (pysoundfile / libsndfile) which supports more formats
                try:
                    import soundfile as sf  # optional dependency
                    data, sample_rate = sf.read(src_path, dtype='float32')
                    # Convert float32 to int16 PCM
                    if data.dtype.kind == 'f':
                        max_val = np.max(np.abs(data)) if data.size > 0 else 0.0
                        if max_val > 0:
                            scaled = (data / max_val) * 0.9
                        else:
                            scaled = data
                        int_data = (scaled * 32767).astype(np.int16)
                    else:
                        int_data = data.astype(np.int16)

                    tmpfd, tmp_path = tempfile.mkstemp(suffix='.wav')
                    os.close(tmpfd)
                    wavfile.write(tmp_path, sample_rate, int_data)
                    return tmp_path
                except Exception as sf_e:
                    print(f" soundfile fallback failed: {sf_e}")
                    # If soundfile isn't available or fails, we'll try ffmpeg below

        # Otherwise, try ffmpeg if available
        if self.ffmpeg_available:
            tmpfd, tmp_path = tempfile.mkstemp(suffix='.wav')
            os.close(tmpfd)
            cmd = [self.ffmpeg_path, '-y', '-i', src_path, '-ar', '16000', '-ac', '1', '-sample_fmt', 's16', tmp_path]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return tmp_path
            except subprocess.CalledProcessError as cpe:
                print(f"ffmpeg conversion failed: {cpe.stderr.decode(errors='ignore')}")
                return None

        # If we reached here and the file was AIFF, it's likely a compressed AIFF
        # that `aifc` couldn't decode and we couldn't convert via soundfile/ffmpeg.
        if encountered_aiff and not self.ffmpeg_available:
            raise RuntimeError(
                "AIFF file appears to use a compressed/unsupported codec. "
                "Install ffmpeg (e.g. `brew install ffmpeg`) or install the Python package "
                "`soundfile` (and libsndfile) so the server can convert AIFF files."
            )

        return None
    
    def transcribe_audio(self, audio_path):
        try:
            # Only use fp16 when CUDA is available; this avoids the
            # "FP16 is not supported on CPU" warning when running on CPU.
            use_fp16 = torch.cuda.is_available()

            # Convert input to a WAV 16-bit file if necessary
            try:
                wav_path = self._convert_to_wav16(audio_path)
            except Exception as conv_err:
                return {'success': False, 'error': f'Audio conversion failed: {str(conv_err)}'}

            if wav_path is None:
                return {
                    'success': False,
                    'error': "Audio conversion failed: ffmpeg not found and file is not a WAV/AIFF that can be processed. Install ffmpeg (e.g. `brew install ffmpeg`) or upload a WAV file."
                }

            # Check if converted file has content
            import os
            if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:
                return {'success': False, 'error': 'Converted audio file is empty or too small'}

            # Check audio duration
            try:
                rate, data = wavfile.read(wav_path)
                duration = len(data) / rate if rate > 0 else 0
                if duration < 0.5:
                    return {'success': False, 'error': f'Audio too short ({duration:.1f}s). Please record at least 0.5 seconds of speech.'}
            except Exception as dur_err:
                return {'success': False, 'error': f'Failed to read audio file: {str(dur_err)}'}

            try:
                result = self.whisper_model.transcribe(wav_path, fp16=use_fp16)
            finally:
                # Clean up temp file if conversion created one
                try:
                    if os.path.abspath(wav_path) != os.path.abspath(audio_path):
                        os.remove(wav_path)
                except Exception:
                    pass

            return {
                'success': True,
                'text': result['text'].strip() if result['text'] else '',
                'language': result.get('language', 'en')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Note: transformers-based translation pipelines were removed. We use
    # `googletrans` (self.google_translator) for translation requests to cover
    # the language pairs configured in `Config.TRANSLATION_MODELS`.
    
    def translate_text(self, text, source_lang='en', target_lang='es'):
        try:
            if text is None:
                return {'success': False, 'error': 'No text provided for translation'}
            
            text = str(text).strip()
            if not text:
                return {'success': False, 'error': 'Empty text provided for translation'}
            
            # A more comprehensive language map for common language codes
            lang_map = {
                'af': 'af','sq': 'sq','am': 'am','ar': 'ar','hy': 'hy','az': 'az',
                'eu': 'eu','be': 'be','bn': 'bn','bs': 'bs','bg': 'bg','ca': 'ca',
                'ceb': 'ceb','zh': 'zh-cn','zh-cn': 'zh-cn','zh-tw': 'zh-tw','co': 'co',
                'hr': 'hr','cs': 'cs','da': 'da','nl': 'nl','en': 'en','eo': 'eo',
                'et': 'et','fi': 'fi','fr': 'fr','fy': 'fy','gl': 'gl','ka': 'ka',
                'de': 'de','el': 'el','gu': 'gu','ht': 'ht','ha': 'ha','haw': 'haw',
                'he': 'he','hi': 'hi','hmn': 'hmn','hu': 'hu','is': 'is','ig': 'ig',
                'id': 'id','ga': 'ga','it': 'it','ja': 'ja','jw': 'jw','kn': 'kn',
                'kk': 'kk','km': 'km','ko': 'ko','ku': 'ku','ky': 'ky','lo': 'lo',
                'la': 'la','lv': 'lv','lt': 'lt','lb': 'lb','mk': 'mk','mg': 'mg',
                'ms': 'ms','ml': 'ml','mt': 'mt','mi': 'mi','mr': 'mr','mn': 'mn',
                'ne': 'ne','no': 'no','ny': 'ny','ps': 'ps','fa': 'fa','pl': 'pl',
                'pt': 'pt','pa': 'pa','ro': 'ro','ru': 'ru','sm': 'sm','gd': 'gd',
                'sr': 'sr','st': 'st','sn': 'sn','sd': 'sd','si': 'si','sk': 'sk',
                'sl': 'sl','so': 'so','es': 'es','su': 'su','sw': 'sw','sv': 'sv',
                'tg': 'tg','ta': 'ta','te': 'te','th': 'th','tr': 'tr','uk': 'uk',
                'ur': 'ur','uz': 'uz','vi': 'vi','cy': 'cy','xh': 'xh','yi': 'yi',
                'yo': 'yo','zu': 'zu'
            }

            src = lang_map.get(source_lang, source_lang)
            dest = lang_map.get(target_lang, target_lang)

            # Use Google Translate for instant translation (covers all languages)
            result = self.google_translator.translate(text, src=src, dest=dest)

            return {
                'success': True,
                'translated_text': result.text if result and result.text else ''
            }

        except Exception as e:
            # If Google Translate fails for any reason, return an error.
            return {
                'success': False,
                'error': str(e)
            }
    
    # transformers-based fallback removed.
    
    def text_to_speech(self, text, output_path=None):
        try:
            if text is None:
                text = ''
            text = str(text).strip()
            if not text:
                return {
                    'success': False,
                    'error': 'No text provided for TTS'
                }
            
            # Ensure the static audio folder exists and save to a file so the client can fetch it
            if output_path is None:
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"tts_{timestamp}.wav"
                output_path = os.path.join('static', 'audio', filename)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Save to file so the web client can fetch and play it
            self.tts_engine.save_to_file(text, output_path)
            self.tts_engine.runAndWait()
            # Verify file was created
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                return {
                    'success': False,
                    'error': 'TTS engine did not produce an output file'
                }

            # Ensure the TTS output is a browser-friendly WAV. Convert AIFF or other
            # containers into WAV16 using our helper (which can use ffmpeg if available).
            corrected = None
            try:
                corrected = self._convert_to_wav16(output_path)
            except Exception as conv_exc:
                print(f"Warning: _convert_to_wav16 raised: {conv_exc}")

            # If conversion helper returned None, try direct ffmpeg conversion as a last resort
            if corrected is None and self.ffmpeg_available:
                try:
                    tmpfd, tmp_path = tempfile.mkstemp(suffix='.wav')
                    os.close(tmpfd)
                    cmd = [self.ffmpeg_path, '-y', '-i', output_path, '-ar', '16000', '-ac', '1', '-sample_fmt', 's16', tmp_path]
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    corrected = tmp_path
                except Exception as ff_err:
                    print(f"ffmpeg final-conversion failed: {ff_err}")
                    corrected = None

            # If we obtained a corrected file, replace the original atomically when possible
            if corrected and os.path.abspath(corrected) != os.path.abspath(output_path):
                try:
                    os.replace(corrected, output_path)
                except Exception:
                    output_path = corrected

            # Final existence check
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                return {
                    'success': False,
                    'error': 'TTS output file missing or zero-length after conversion attempts'
                }

            return {
                'success': True,
                'output_path': output_path,
                'url': f"/{output_path}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_available_languages(self):
        # Expanded language list (~50 common languages)
        languages = {
            'af': 'Afrikaans','sq': 'Albanian','am': 'Amharic','ar': 'Arabic','hy': 'Armenian',
            'az': 'Azerbaijani','eu': 'Basque','be': 'Belarusian','bn': 'Bengali','bs': 'Bosnian',
            'bg': 'Bulgarian','ca': 'Catalan','ceb': 'Cebuano','zh': 'Chinese (Simplified)','zh-tw': 'Chinese (Traditional)',
            'co': 'Corsican','hr': 'Croatian','cs': 'Czech','da': 'Danish','nl': 'Dutch',
            'en': 'English','eo': 'Esperanto','et': 'Estonian','fi': 'Finnish','fr': 'French',
            'fy': 'Frisian','gl': 'Galician','ka': 'Georgian','de': 'German','el': 'Greek',
            'gu': 'Gujarati','ht': 'Haitian Creole','ha': 'Hausa','he': 'Hebrew','hi': 'Hindi',
            'hu': 'Hungarian','is': 'Icelandic','ig': 'Igbo','id': 'Indonesian','ga': 'Irish',
            'it': 'Italian','ja': 'Japanese','jw': 'Javanese','kn': 'Kannada','kk': 'Kazakh',
            'km': 'Khmer','ko': 'Korean','ku': 'Kurdish','ky': 'Kyrgyz','lo': 'Lao',
            'la': 'Latin','lv': 'Latvian','lt': 'Lithuanian','lb': 'Luxembourgish','mk': 'Macedonian',
            'mg': 'Malagasy','ms': 'Malay','ml': 'Malayalam','mt': 'Maltese','mi': 'Maori',
            'mr': 'Marathi','mn': 'Mongolian','ne': 'Nepali','no': 'Norwegian','pl': 'Polish',
            'pt': 'Portuguese','ro': 'Romanian','ru': 'Russian','sr': 'Serbian','sk': 'Slovak',
            'sl': 'Slovenian','es': 'Spanish','sw': 'Swahili','sv': 'Swedish','tl': 'Filipino',
            'ta': 'Tamil','te': 'Telugu','th': 'Thai','tr': 'Turkish','uk': 'Ukrainian',
            'ur': 'Urdu','vi': 'Vietnamese','cy': 'Welsh','xh': 'Xhosa','yi': 'Yiddish',
            'yo': 'Yoruba','zu': 'Zulu'
        }

        return languages