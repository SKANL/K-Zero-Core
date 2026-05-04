"""
Módulo de síntesis de voz (TTS) usando edge-tts y pygame.

Provee:
    TextToSpeech: Sintetiza texto a voz usando las voces neurales de Microsoft
                  edge-tts y lo reproduce a través de pygame.mixer.
"""

import asyncio
import logging
import os
from tempfile import NamedTemporaryFile
from typing import Optional

import edge_tts
import pygame

from k_zero_core.audio.config import TtsConfig

logger = logging.getLogger(__name__)


class TextToSpeech:
    """
    Sintetiza texto a voz con edge-tts y lo reproduce con pygame.

    La instancia puede reutilizarse para múltiples llamadas a speak().
    El mixer de pygame se inicializa una sola vez en el constructor.
    """

    def __init__(self, config: Optional[TtsConfig] = None):
        """
        Inicializa el motor TTS y el mixer de pygame.

        Args:
            config: Instancia de TtsConfig. Si es None, se crea desde env-vars.
        """
        self.config = config or TtsConfig.from_env()
        self.default_voice = self.config.voice
        self._init_mixer()

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    @staticmethod
    def _init_mixer() -> None:
        """
        Inicializa pygame.mixer si no está ya inicializado.

        Verificar antes de inicializar previene el error 'pygame.error: mixer not initialized'
        en escenarios donde TextToSpeech se instancia más de una vez.
        """
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
                logger.debug("pygame.mixer inicializado correctamente.")
            except pygame.error as e:
                logger.error("No se pudo inicializar pygame.mixer: %s", e)
                raise

    async def _synthesize_and_play(self, text: str, voice: str) -> None:
        """
        Genera el audio con edge-tts y lo reproduce de forma bloqueante.

        Utiliza un archivo temporal que se elimina garantizadamente en el bloque
        finally, incluso si la reproducción falla.

        Args:
            text : Texto a sintetizar.
            voice: ID de voz de edge-tts.
        """
        if not text.strip():
            return

        communicate = edge_tts.Communicate(text, voice)

        # NamedTemporaryFile con delete=False: el archivo existe hasta que lo borramos
        with NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            temp_path = tmp.name

        try:
            await communicate.save(temp_path)

            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            # Esperar a que termine la reproducción sin bloquear el event loop
            import time
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)

            pygame.mixer.music.unload()

        except pygame.error as e:
            logger.error("Error en pygame durante la reproducción de TTS: %s", e)
        except Exception as e:
            logger.error("Error inesperado en TTS: %s", e)
        finally:
            # Garantizar limpieza del archivo temporal en cualquier caso
            try:
                from pathlib import Path
                Path(temp_path).unlink(missing_ok=True)
            except OSError as e:
                logger.warning("No se pudo eliminar el archivo temporal de TTS '%s': %s", temp_path, e)

    def speak(self, text: str, voice: Optional[str] = None) -> None:
        """
        Sintetiza y reproduce el texto de forma síncrona.

        Detecta si hay un event loop de asyncio activo para compatibilidad con
        contextos síncronos y asíncronos:
            - Sin loop activo (caso habitual CLI): usa asyncio.run().
            - Con loop activo (entornos async): usa loop.run_until_complete()
              con un ThreadPoolExecutor para no bloquear el loop.

        Args:
            text : Texto a sintetizar y reproducir.
            voice: ID de voz de edge-tts. Si es None, usa self.default_voice.
        """
        target_voice = voice or self.default_voice
        coro = self._synthesize_and_play(text, target_voice)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Hay un event loop activo: ejecutar en un thread separado para no bloquearlo
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                future.result()
        else:
            asyncio.run(coro)
