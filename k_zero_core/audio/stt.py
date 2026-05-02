import io
import wave
import speech_recognition as sr
from faster_whisper import WhisperModel
from k_zero_core.core.exceptions import APIVoiceException

class SpeechTranscriber:
    def __init__(self, model_size: str = "base", device: str = "cpu"):
        print("[Iniciando modelo de reconocimiento de voz... esto puede tomar un momento la primera vez]")
        self.model = WhisperModel(model_size, device=device, compute_type="int8")
        self.recognizer = sr.Recognizer()
        # Adjust recognizer sensitivity
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    def listen_and_transcribe(self) -> str:
        """Listens to the microphone and transcribes the speech to text."""
        with sr.Microphone() as source:
            print("\n Ajustando al ruido ambiente... ", end="", flush=True)
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("¡Habla ahora!")
            
            try:
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=30)
            except sr.WaitTimeoutError:
                print("⏳ No se detectó voz.")
                return ""
            
            print("⏳ Transcribiendo...")
            
            # Convert audio data to a file-like object for Whisper
            wav_data = audio.get_wav_data()
            wav_stream = io.BytesIO(wav_data)
            
            # Transcribe
            segments, info = self.model.transcribe(wav_stream, beam_size=5)
            
            text = "".join([segment.text for segment in segments])
            return text.strip()
