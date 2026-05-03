"""
Módulo de audio de K-Zero-Core.

Exporta el API público completo para que los consumidores puedan importar
directamente desde `k_zero_core.audio` sin conocer la estructura interna.

Ejemplo de uso::

    from k_zero_core.audio import SpeechTranscriber, TextToSpeech, IOHandler, WhisperConfig

    config = WhisperConfig(model_size="medium", language="es")
    stt = SpeechTranscriber(config=config)
    tts = TextToSpeech()
    texto = stt.listen_walkie_talkie()
    tts.speak(texto)
"""

from k_zero_core.audio.config import WhisperConfig, TtsConfig
from k_zero_core.audio.stt import SpeechTranscriber, CustomMicrophone
from k_zero_core.audio.tts import TextToSpeech
from k_zero_core.audio.io_handler import IOHandler
from k_zero_core.audio.downloader import MediaDownloader
from k_zero_core.audio.sources import get_audio_devices, get_running_applications

__all__ = [
    # Configuración
    "WhisperConfig",
    "TtsConfig",
    # STT
    "SpeechTranscriber",
    "CustomMicrophone",
    # TTS
    "TextToSpeech",
    # I/O
    "IOHandler",
    # Utilidades
    "MediaDownloader",
    "get_audio_devices",
    "get_running_applications",
]
