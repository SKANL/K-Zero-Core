import os
import time
import edge_tts
import pygame
import asyncio
from tempfile import NamedTemporaryFile

class TextToSpeech:
    def __init__(self, default_voice: str = "es-MX-DaliaNeural"):
        self.default_voice = default_voice
        # Initialize pygame mixer
        pygame.mixer.init()

    async def _generate_and_play(self, text: str, voice: str) -> None:
        if not text.strip():
            return
            
        communicate = edge_tts.Communicate(text, voice)
        
        # We need a temporary file to save the audio
        with NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_path = temp_audio.name
            
        try:
            await communicate.save(temp_path)
            
            # Play with pygame
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            
            # Wait until it finishes playing
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            # Unload before trying to delete
            pygame.mixer.music.unload()
            
        finally:
            # Clean up the file
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                print(f"No se pudo eliminar el archivo temporal de audio: {e}")

    def speak(self, text: str, voice: str = None) -> None:
        """Synthesize and play the text synchronously."""
        v = voice or self.default_voice
        asyncio.run(self._generate_and_play(text, v))
