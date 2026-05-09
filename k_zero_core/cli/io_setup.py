"""Construcción de IOHandler para la CLI."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from k_zero_core.audio.io_handler import IOHandler


def setup_io_handler(
    input_type: str,
    output_type: str,
    plugin: Any,
    *,
    choose_stt_config_func: Callable[[], dict] | None = None,
    speech_transcriber_cls: type | None = None,
    text_to_speech_cls: type | None = None,
    whisper_config_cls: type | None = None,
    tts_config_cls: type | None = None,
) -> IOHandler:
    """Configura y retorna el IOHandler resolviendo dependencias de audio de forma lazy."""
    stt = None
    tts = None
    stt_config = {}

    if input_type == "audio":
        from k_zero_core.audio.config import WhisperConfig
        from k_zero_core.audio.stt import SpeechTranscriber
        from k_zero_core.cli.menus import choose_stt_config

        choose_stt_config_func = choose_stt_config_func or choose_stt_config
        whisper_config_cls = whisper_config_cls or WhisperConfig
        speech_transcriber_cls = speech_transcriber_cls or SpeechTranscriber

        stt_config = choose_stt_config_func()
        whisper_cfg = whisper_config_cls.from_env()
        whisper_cfg.model_size = stt_config.get("model_size") or whisper_cfg.model_size
        whisper_cfg.language = stt_config.get("language")
        stt = speech_transcriber_cls(config=whisper_cfg)

    if output_type == "audio":
        from k_zero_core.audio.config import TtsConfig
        from k_zero_core.audio.tts import TextToSpeech

        tts_config_cls = tts_config_cls or TtsConfig
        text_to_speech_cls = text_to_speech_cls or TextToSpeech

        tts_cfg = tts_config_cls(voice=plugin.get_voice())
        tts = text_to_speech_cls(config=tts_cfg)

    return IOHandler(input_type, output_type, stt, tts, stt_config)
