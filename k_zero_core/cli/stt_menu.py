"""Menú interactivo para configurar captura STT."""
from typing import Any

from k_zero_core.audio.sources import get_audio_devices

AUDIO_SOURCES = [
    ("mic", "Micrófono (Walkie-Talkie - espera silencio)"),
    ("mic_stream", "Micrófono (Streaming / Tiempo Real)"),
    ("loopback", "Audio del Sistema Completo (Loopback / Grabar reuniones)"),
    ("file", "Archivo Local (.mp3, .wav)"),
    ("youtube", "URL de YouTube"),
]

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v3"]

TRANSCRIPTION_LANGUAGES = [
    ("es", "Español (Más rápido)"),
    ("en", "Inglés"),
    (None, "Autodetectar (Penalización de latencia)"),
]

LIVE_AUDIO_SOURCES = {"mic", "mic_stream", "loopback"}


def _choose_live_device(source_key: str) -> int | None:
    """Solicita dispositivo de micrófono/loopback para una fuente en vivo."""
    mics, loopbacks = get_audio_devices()
    devices = loopbacks if source_key == "loopback" else mics

    if not devices:
        source_label = "loopback" if source_key == "loopback" else "micrófono"
        print(f"⚠️ No se detectaron dispositivos de {source_label}. Se usará el por defecto.")
        return None

    print("\n=== Dispositivos Disponibles ===")
    print("0. Dispositivo por Defecto del Sistema")
    for index, (_device_index, device_name) in enumerate(devices):
        print(f"{index + 1}. {device_name}")

    selection = input(f"\nElige un dispositivo (0 - {len(devices)}): ").strip()
    try:
        selected_index = int(selection)
    except ValueError:
        return None

    if 0 < selected_index <= len(devices):
        return devices[selected_index - 1][0]
    return None


def choose_stt_config(select_from_list) -> dict[str, Any]:
    """Prompt the user for Advanced STT configuration."""
    config: dict[str, Any] = {}

    print("\n=== Fuente de Audio para Transcripción ===")
    for index, (_source_key, label) in enumerate(AUDIO_SOURCES):
        print(f"{index + 1}. {label}")

    source_index = select_from_list(
        f"\nElige una opción (1 - {len(AUDIO_SOURCES)}): ", AUDIO_SOURCES
    )
    source_key = AUDIO_SOURCES[source_index][0]
    config["source"] = source_key

    if source_key in LIVE_AUDIO_SOURCES:
        config["device_index"] = _choose_live_device(source_key)
    elif source_key == "file":
        config["filepath"] = input("\nIntroduce la ruta absoluta del archivo de audio: ").strip()
    elif source_key == "youtube":
        config["youtube_url"] = input("\nIntroduce la URL de YouTube: ").strip()

    print("\n=== Tamaño del Modelo de Whisper ===")
    for index, model in enumerate(WHISPER_MODELS):
        print(f"{index + 1}. {model}")
    model_index = select_from_list(
        f"\nElige un modelo (1 - {len(WHISPER_MODELS)}): ", WHISPER_MODELS
    )
    config["model_size"] = WHISPER_MODELS[model_index]

    print("\n=== Idioma de Transcripción ===")
    for index, (_language, label) in enumerate(TRANSCRIPTION_LANGUAGES):
        print(f"{index + 1}. {label}")
    language_index = select_from_list(
        f"\nElige un idioma (1 - {len(TRANSCRIPTION_LANGUAGES)}): ",
        TRANSCRIPTION_LANGUAGES,
    )
    config["language"] = TRANSCRIPTION_LANGUAGES[language_index][0]

    return config
