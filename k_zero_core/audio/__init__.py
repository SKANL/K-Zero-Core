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

_LAZY_EXPORTS = {
    "WhisperConfig": ("k_zero_core.audio.config", "WhisperConfig"),
    "TtsConfig": ("k_zero_core.audio.config", "TtsConfig"),
    "SpeechTranscriber": ("k_zero_core.audio.stt", "SpeechTranscriber"),
    "CustomMicrophone": ("k_zero_core.audio.stt", "CustomMicrophone"),
    "TextToSpeech": ("k_zero_core.audio.tts", "TextToSpeech"),
    "IOHandler": ("k_zero_core.audio.io_handler", "IOHandler"),
    "MediaDownloader": ("k_zero_core.audio.downloader", "MediaDownloader"),
    "get_audio_devices": ("k_zero_core.audio.sources", "get_audio_devices"),
    "get_running_applications": ("k_zero_core.audio.sources", "get_running_applications"),
}


def __getattr__(name: str):
    """Exporta el API público sin cargar STT/TTS hasta que se pidan explícitamente."""
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module 'k_zero_core.audio' has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    from importlib import import_module
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value

__all__ = [
    "WhisperConfig",
    "TtsConfig",
    "SpeechTranscriber",
    "CustomMicrophone",
    "TextToSpeech",
    "IOHandler",
    "MediaDownloader",
    "get_audio_devices",
    "get_running_applications",
]
