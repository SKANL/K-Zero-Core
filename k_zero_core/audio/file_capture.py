"""Captura de audio desde fuentes de archivo o YouTube."""
from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

FILE_SOURCE = "file"
YOUTUBE_SOURCE = "youtube"
FILE_SOURCES = frozenset({FILE_SOURCE, YOUTUBE_SOURCE})


def _download_youtube_audio(url: str) -> str:
    """Descarga audio de YouTube usando el downloader configurado."""
    from k_zero_core.audio.downloader import MediaDownloader

    return MediaDownloader.download_youtube_audio(url)


def transcribe_file_source(
    stt: Any,
    stt_config: dict,
    source: str,
    *,
    download_youtube_audio_func: Callable[[str], str] = _download_youtube_audio,
) -> str:
    """
    Transcribe una fuente de archivo local o YouTube.

    Args:
        stt: Objeto con método transcribe_file(path).
        stt_config: Configuración de captura con filepath o youtube_url.
        source: Tipo de fuente: "file" o "youtube".
        download_youtube_audio_func: Función inyectable para descargar audio.

    Returns:
        Texto transcrito o cadena vacía si falta configuración.
    """
    if source == FILE_SOURCE:
        filepath = stt_config.get("filepath", "")
        if not filepath:
            logger.error("stt_config['filepath'] no está definido.")
            return ""
        return stt.transcribe_file(filepath)

    if source != YOUTUBE_SOURCE:
        logger.error("Fuente de archivo desconocida: '%s'.", source)
        return ""

    url = stt_config.get("youtube_url", "")
    if not url:
        logger.error("stt_config['youtube_url'] no está definido.")
        return ""

    audio_path = download_youtube_audio_func(url)
    try:
        return stt.transcribe_file(audio_path)
    finally:
        _remove_temp_audio(audio_path)


def _remove_temp_audio(audio_path: str) -> None:
    """Elimina un archivo temporal de audio si existe."""
    if not os.path.exists(audio_path):
        return
    try:
        os.remove(audio_path)
        logger.debug("Archivo temporal YouTube eliminado: %s", audio_path)
    except OSError as e:
        logger.warning("No se pudo eliminar '%s': %s", audio_path, e)
