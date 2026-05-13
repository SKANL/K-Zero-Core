"""
Módulo de gestión de Entrada/Salida para el sistema de interacción.

Provee:
    IOHandler: Abstracción unificada de entrada (texto/voz) y salida (texto/voz)
               que desacopla los modos de interacción del hardware de audio.
"""

import logging

from k_zero_core.audio.file_capture import FILE_SOURCES, transcribe_file_source
from k_zero_core.modes.conversation_flow import EXIT_COMMANDS

logger = logging.getLogger(__name__)

_STREAMING_SOURCES = frozenset({"mic_stream"})
_LIVE_SOURCES = frozenset({"mic", "mic_stream", "loopback"})


class IOHandler:
    """
    Abstracción de Entrada/Salida que desacopla los modos de la infraestructura de audio.

    Soporta cuatro combinaciones de I/O:
        text  → text  : Modo silencioso (input/print)
        audio → audio : Manos libres completo (STT + TTS)
        text  → audio : Escritura + escuchar respuesta (TTS)
        audio → text  : Dictado solo (STT + print)

    Atributos:
        input_type : 'text' o 'audio'.
        output_type: 'text' o 'audio'.
    """

    def __init__(
        self,
        input_type: str,
        output_type: str,
        stt=None,
        tts=None,
        stt_config: dict | None = None,
    ):
        """
        Args:
            input_type : Tipo de entrada: 'text' o 'audio'.
            output_type: Tipo de salida: 'text' o 'audio'.
            stt        : Instancia de SpeechTranscriber (requerida si input_type='audio').
            tts        : Instancia de TextToSpeech (requerida si output_type='audio').
            stt_config : Diccionario de configuración de captura de audio con claves:
                             source       : 'mic' | 'mic_stream' | 'loopback' | 'file' | 'youtube'
                             device_index : int | None
                             filepath     : str (requerido si source='file')
                             youtube_url  : str (requerido si source='youtube')
        """
        self.input_type = input_type
        self.output_type = output_type
        self.stt = stt
        self.tts = tts
        self.stt_config: dict = stt_config or {}
        self._file_transcribed = False

    def get_user_input(self) -> str:
        """
        Obtiene la entrada del usuario según el tipo de I/O configurado.

        Para entrada de texto: muestra el prompt "Tú: " y lee desde stdin.
        Para entrada de audio: delega al método de captura correcto según 'source'.

        Returns:
            Texto introducido o transcrito. Cadena vacía si no hubo entrada.
        """
        if self.input_type != "audio" or not self.stt:
            return input("Tú: ")

        return self._capture_audio()

    def output_response(self, text: str) -> None:
        """
        Emite la respuesta del sistema según el tipo de salida configurado.

        Para salida de texto: no hace nada (el llamador ya imprimió la respuesta).
        Para salida de audio: sintetiza y reproduce el texto con TTS.

        Args:
            text: Texto de la respuesta a emitir.
        """
        if self.output_type != "audio" or not self.tts:
            return

        if not text.strip():
            return

        logger.debug("Iniciando TTS para respuesta de %d caracteres.", len(text))
        print("🔊 Hablando...")
        self.tts.speak(text, voice=self.tts.default_voice)

    def _capture_audio(self) -> str:
        """
        Enruta la captura al método correcto según la fuente configurada.

        Returns:
            Texto capturado/transcrito, o el comando de salida si la fuente de archivo
            ya fue procesada (finaliza la sesión automáticamente).
        """
        source = self.stt_config.get("source", "mic")

        if source in FILE_SOURCES:
            return self._capture_from_file(source)

        if source in _LIVE_SOURCES:
            return self._capture_live(source)

        logger.warning("Fuente de audio desconocida: '%s'. Usando entrada de texto.", source)
        return input("Tú: ")

    def _capture_from_file(self, source: str) -> str:
        """
        Transcribe un archivo local o URL de YouTube (solo una vez por sesión).

        Tras la primera transcripción retorna el comando de salida para que el modo
        principal termine la sesión automáticamente.

        Args:
            source: 'file' o 'youtube'.

        Returns:
            Texto transcrito en el primer llamado; comando de salida en los siguientes.
        """
        if self._file_transcribed:
            return EXIT_COMMANDS[0]

        self._file_transcribed = True

        return transcribe_file_source(self.stt, self.stt_config, source)

    def _capture_live(self, source: str) -> str:
        """
        Captura audio en tiempo real desde micrófono o loopback.

        Args:
            source: 'mic', 'mic_stream' o 'loopback'.

        Returns:
            Texto transcrito desde el audio capturado.
        """
        device_index: int | None = self.stt_config.get("device_index")
        is_loopback = source == "loopback"

        if source in _STREAMING_SOURCES:
            return self.stt.listen_streaming(
                device_index=device_index,
                is_loopback=is_loopback,
            )

        return self.stt.listen_walkie_talkie(
            device_index=device_index,
            is_loopback=is_loopback,
        )
