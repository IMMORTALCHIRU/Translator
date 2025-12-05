import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wavfile
import os
from datetime import datetime

class AudioProcessor:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
    
    def record_audio(self, duration=5, output_path=None):
        try:
            print(f"Recording for {duration} seconds...")
            audio_data = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32'
            )
            sd.wait()  # Wait for recording to complete
            
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"static/audio/recording_{timestamp}.wav"
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save as WAV file
            wavfile.write(output_path, self.sample_rate, audio_data)
            
            return {
                'success': True,
                'path': output_path
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_uploaded_audio(self, file_storage, upload_folder='static/audio'):
        try:
            # Create upload folder if it doesn't exist
            os.makedirs(upload_folder, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"upload_{timestamp}_{file_storage.filename}"
            filepath = os.path.join(upload_folder, filename)
            
            # Save file
            file_storage.save(filepath)
            
            return {
                'success': True,
                'path': filepath
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }