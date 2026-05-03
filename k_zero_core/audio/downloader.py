"""
Módulo de descarga de medios para el sistema de audio.

Provee:
    MediaDownloader: Descarga audio de fuentes externas (YouTube, etc.) a archivos
                     temporales únicos usando yt-dlp e imageio-ffmpeg.
"""

import logging
import os
import tempfile

from k_zero_core.core.exceptions import APIVoiceException

logger = logging.getLogger(__name__)

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


class MediaDownloader:
    """Utilidades para descargar archivos multimedia de fuentes externas."""

    @staticmethod
    def download_youtube_audio(url: str) -> str:
        """
        Descarga el audio de un video de YouTube a un archivo temporal único.

        Usa yt-dlp para la descarga y ffmpeg (via imageio-ffmpeg) para la
        conversión a MP3. El archivo temporal tiene nombre único generado con
        tempfile para evitar colisiones en llamadas concurrentes.

        Args:
            url: URL del video de YouTube.

        Returns:
            Ruta absoluta al archivo MP3 descargado. El llamador es responsable
            de eliminar el archivo cuando ya no lo necesite.

        Raises:
            APIVoiceException: Si yt-dlp no está instalado, si la descarga falla,
                               o si el archivo resultante no existe.
        """
        if not yt_dlp:
            raise APIVoiceException(
                "yt-dlp no está instalado. Instálalo con: uv pip install yt-dlp"
            )

        logger.info("Descargando audio de YouTube: %s", url)
        print(f"⏳ Descargando audio de YouTube... ({url})")

        # Crear un archivo temporal con nombre único para evitar colisiones
        tmp_fd, tmp_path_base = tempfile.mkstemp(prefix="yt_audio_", suffix=".tmp")
        os.close(tmp_fd)  # Solo necesitamos el nombre, no el descriptor
        # Eliminar el .tmp para que yt-dlp pueda crear el .mp3 con el mismo stem
        os.remove(tmp_path_base)

        # El stem del archivo (sin extensión) se usa como plantilla para yt-dlp
        output_stem = tmp_path_base[:-4]  # remover ".tmp"
        audio_path = output_stem + ".mp3"

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_stem + ".%(ext)s",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "quiet": True,
            "no_warnings": True,
        }

        # Usar ffmpeg bundled de imageio-ffmpeg si está disponible
        try:
            import imageio_ffmpeg
            ydl_opts["ffmpeg_location"] = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            logger.debug("imageio-ffmpeg no encontrado, usando ffmpeg del PATH.")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            # Limpiar cualquier archivo parcial si la descarga falla
            for ext in (".mp3", ".webm", ".m4a", ".opus", ".tmp"):
                partial = output_stem + ext
                if os.path.exists(partial):
                    try:
                        os.remove(partial)
                    except OSError:
                        pass
            raise APIVoiceException(f"Error al descargar audio de YouTube: {e}") from e

        if not os.path.exists(audio_path):
            raise APIVoiceException(
                f"La descarga completó pero no se encontró el archivo MP3 esperado: {audio_path}"
            )

        logger.info("Audio descargado exitosamente: %s", audio_path)
        return audio_path
