"""
Módulo de transcripción de voz a texto (STT) usando faster-whisper.

Provee:
    - CustomMicrophone : Subclase de sr.Microphone con soporte WASAPI loopback.
    - SpeechTranscriber: Clase principal que gestiona el modelo Whisper y los
                         modos de captura de audio (walkie-talkie, streaming, archivo).
"""

import io
import logging
import os
import sys
from typing import Optional

# pyaudiowpatch debe importarse antes que SpeechRecognition en Windows para que
# el alias 'pyaudio' apunte a la versión con soporte WASAPI loopback.
try:
    import pyaudiowpatch as pyaudio
    sys.modules["pyaudio"] = pyaudio
except ImportError:
    pass

import speech_recognition as sr
from faster_whisper import WhisperModel

from k_zero_core.audio.config import WhisperConfig
from k_zero_core.core.exceptions import APIVoiceException

logger = logging.getLogger(__name__)


class CustomMicrophone(sr.Microphone):
    """
    Subclase de Microphone que detecta automáticamente los canales y sample rate
    requeridos por el dispositivo.

    Indispensable para dispositivos Loopback WASAPI en Windows, que requieren 2+
    canales y deben usar el sample rate nativo del dispositivo (usualmente 48000 Hz).
    """

    def __enter__(self) -> "CustomMicrophone":
        """
        Abre el stream de audio adaptándose a los canales y sample rate del dispositivo.

        Returns:
            La instancia del micrófono con el stream abierto.

        Raises:
            Exception: Re-lanza cualquier error de PyAudio cerrando el contexto correctamente.
        """
        assert self.stream is None, "Esta fuente de audio ya está dentro de un context manager"
        self.audio = self.pyaudio_module.PyAudio()
        try:
            if self.device_index is not None:
                device_info = self.audio.get_device_info_by_index(self.device_index)
            else:
                device_info = self.audio.get_default_input_device_info()

            # Adaptar a los canales y sample rate nativos del dispositivo.
            # Esto es crítico para dispositivos WASAPI loopback (estéreo 48kHz).
            channels = int(device_info.get("maxInputChannels", 1))
            native_rate = int(device_info.get("defaultSampleRate", self.SAMPLE_RATE))
            self.SAMPLE_RATE = native_rate

            self.stream = sr.Microphone.MicrophoneStream(
                self.audio.open(
                    input_device_index=self.device_index,
                    channels=channels,
                    format=self.format,
                    rate=self.SAMPLE_RATE,
                    frames_per_buffer=self.CHUNK,
                    input=True,
                )
            )
        except Exception:
            self.audio.terminate()
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Cierra el stream y termina PyAudio correctamente."""
        try:
            self.stream.close()
        finally:
            self.stream = None
            self.audio.terminate()


class SpeechTranscriber:
    """
    Gestiona la inicialización y uso del modelo Whisper para transcripción de voz.

    Soporta tres modos de captura:
        - listen_walkie_talkie : Captura un único turno de habla hasta detectar silencio.
        - listen_streaming     : Captura continua en chunks y acumula resultados.
        - transcribe_file      : Transcribe un archivo de audio local o un objeto BytesIO.
    """

    def __init__(self, config: Optional[WhisperConfig] = None):
        """
        Inicializa el modelo Whisper y el reconocedor de SpeechRecognition.

        Args:
            config: Instancia de WhisperConfig. Si es None, se crea desde env-vars.
        """
        self.config = config or WhisperConfig.from_env()

        # Determinar dispositivo de inferencia y tipo de cuantización
        self._device, self._compute_type = self._resolve_device(self.config.device)

        logger.info(
            "Iniciando Whisper (%s) en %s con %s...",
            self.config.model_size,
            self._device.upper(),
            self._compute_type,
        )
        print(f"⚙️  Iniciando Whisper ({self.config.model_size}) en {self._device.upper()} con {self._compute_type}...")

        self.model = self._load_model()

        # SpeechRecognition gestiona la captura de audio desde pyaudio
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = self.config.energy_threshold
        self.recognizer.dynamic_energy_threshold = True
        # pause_threshold >= non_speaking_duration es un invariante de SR
        self.recognizer.pause_threshold = 0.6
        self.recognizer.non_speaking_duration = 0.5
        self._ambient_adjusted = False

    # ------------------------------------------------------------------
    # Métodos privados de inicialización
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_device(device: Optional[str]) -> tuple[str, str]:
        """
        Determina el dispositivo de inferencia y el tipo de cuantización óptimos.

        Args:
            device: Dispositivo preferido ('cuda', 'cpu') o None para autodetectar.

        Returns:
            Tupla (device, compute_type).
        """
        if device:
            return device, "float16" if device == "cuda" else "int8"

        # Por defecto, intentamos CUDA primero.
        # Si la máquina no tiene GPU o fallan las librerías,
        # _load_model se encargará de hacer el fallback seguro a CPU.
        return "cuda", "float16"

    def _load_model(self) -> WhisperModel:
        """
        Carga el modelo Whisper con fallback a CPU si CUDA falla o si estamos en Mac.
        """
        import platform
        # Detectar Mac explícitamente para evitar intentar CUDA
        if platform.system() == "Darwin":
            self._device = "cpu"
            # Faster-Whisper usa Accelerate en CPU (Mac) de forma nativa
            self._compute_type = "int8"

        try:
            return WhisperModel(
                self.config.model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
        except Exception as e:
            if self._device == "cuda":
                logger.warning("CUDA falló, haciendo fallback a CPU: %s", e)
                print(f"⚠️  CUDA falló, usando CPU: {e}")
                self._device = "cpu"
                self._compute_type = "int8"
                try:
                    return WhisperModel(
                        self.config.model_size,
                        device=self._device,
                        compute_type=self._compute_type,
                    )
                except Exception as cpu_e:
                    raise APIVoiceException(f"Error al inicializar Whisper en CPU: {cpu_e}") from cpu_e
            raise APIVoiceException(f"Error al inicializar Whisper: {e}") from e

    # ------------------------------------------------------------------
    # Métodos privados de transcripción
    # ------------------------------------------------------------------

    def _do_transcribe(self, audio_source) -> str:
        """
        Ejecuta la transcripción usando el modelo Whisper con la configuración activa.

        Aplica:
            - VAD estricto con parámetros completos (threshold, durations, padding).
            - Temperatura de fallback secuencial para evitar greedy decoding.
            - condition_on_previous_text=False para prevenir bucles de alucinación.

        Args:
            audio_source: Ruta a archivo de audio (str/Path) o BytesIO con datos WAV.

        Returns:
            Texto transcrito, limpio de espacios. Cadena vacía si no hay voz.
        """
        cfg = self.config
        segments, _info = self.model.transcribe(
            audio_source,
            language=cfg.language,
            beam_size=cfg.beam_size,
            best_of=cfg.best_of,
            temperature=cfg.temperature,
            compression_ratio_threshold=cfg.compression_ratio_threshold,
            log_prob_threshold=cfg.log_prob_threshold,
            no_speech_threshold=cfg.no_speech_threshold,
            condition_on_previous_text=cfg.condition_on_previous_text,
            vad_filter=cfg.vad_filter,
            vad_parameters=cfg.get_vad_parameters(),
        )
        return "".join(segment.text for segment in segments).strip()

    def _configure_for_loopback(self) -> None:
        """Ajusta el reconocedor para captura loopback digital (umbral fijo, sin ajuste ambiental)."""
        self.recognizer.energy_threshold = 100
        self.recognizer.dynamic_energy_threshold = False

    def _adjust_ambient_noise(self, source: sr.AudioSource) -> None:
        """Calibra el umbral de energía al ruido ambiente (solo si no se hizo ya)."""
        if not self._ambient_adjusted:
            print("🔈 Ajustando al ruido ambiente...", end=" ", flush=True)
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self._ambient_adjusted = True
            print("Listo.")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def listen_walkie_talkie(
        self,
        device_index: Optional[int] = None,
        is_loopback: bool = False,
    ) -> str:
        """
        Modo walkie-talkie: escucha un único bloque de habla y lo transcribe.

        Bloquea hasta detectar silencio o timeout. Ideal para interacciones
        turno a turno donde el usuario habla, para, y espera respuesta.

        Args:
            device_index: Índice PyAudio del dispositivo de entrada. None = default.
            is_loopback : True si el dispositivo es WASAPI loopback (audio del sistema).

        Returns:
            Texto transcrito. Cadena vacía si no se detectó voz o hubo timeout.
        """
        with CustomMicrophone(device_index=device_index) as source:
            if is_loopback:
                self._configure_for_loopback()
            else:
                self._adjust_ambient_noise(source)

            print("🎙️  ¡Habla ahora! (Se detendrá al detectar silencio)")
            try:
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=60)
            except sr.WaitTimeoutError:
                print("⏳ No se detectó voz en el tiempo límite.")
                return ""

        print("⏳ Transcribiendo...", end="\r")
        resultado = self._do_transcribe(io.BytesIO(audio.get_wav_data()))
        print(" " * 30, end="\r")  # Limpiar línea de estado
        return resultado

    def listen_streaming(
        self,
        device_index: Optional[int] = None,
        is_loopback: bool = False,
    ) -> str:
        """
        Modo streaming: captura continua en chunks y acumula transcripciones en tiempo real.

        El stream permanece abierto durante toda la sesión dentro de un único context
        manager. La captura termina tras 'silence_timeout' segundos de silencio con texto
        acumulado, o 'max_idle_timeout' segundos sin haber detectado voz alguna.

        Args:
            device_index: Índice PyAudio del dispositivo. None = default.
            is_loopback : True si es WASAPI loopback.

        Returns:
            Todo el texto acumulado unido por espacios.
        """
        import queue
        import time

        audio_queue: queue.Queue = queue.Queue()
        silence_timeout = 2.0   # Segundos de silencio para terminar el turno
        max_idle_timeout = 10.0  # Segundos máximos sin detectar voz alguna

        def _on_audio_captured(recognizer: sr.Recognizer, audio: sr.AudioData) -> None:
            audio_queue.put(audio)

        # Ajustes previos al context manager (solo loopback, no necesita stream abierto)
        if is_loopback:
            self._configure_for_loopback()

        # Corregido: Todo el ciclo de vida del stream ocurre dentro del with.
        # El context manager debe estar abierto cuando listen_in_background inicia.
        with CustomMicrophone(device_index=device_index) as source:
            if not is_loopback:
                self._adjust_ambient_noise(source)

            # Permitir mayor pausa en modo streaming para no cortar al usuario mientras respira
            # Invariante: pause_threshold >= non_speaking_duration
            self.recognizer.pause_threshold = 0.8
            self.recognizer.non_speaking_duration = 0.5

            print("🎙️  [Streaming] Habla ahora... (Silencio de 2s para terminar)")
            stop_listening = self.recognizer.listen_in_background(
                source, _on_audio_captured, phrase_time_limit=15
            )

            final_text: list[str] = []
            last_speech_time = time.time()

            try:
                while True:
                    try:
                        audio = audio_queue.get(timeout=0.2)
                        last_speech_time = time.time()
                        text = self._do_transcribe(io.BytesIO(audio.get_wav_data()))
                        if text:
                            print(f"➜ {text}", flush=True)
                            final_text.append(text)
                    except queue.Empty:
                        elapsed = time.time() - last_speech_time
                        if elapsed > silence_timeout and final_text:
                            break
                        if elapsed > max_idle_timeout and not final_text:
                            break
            finally:
                stop_listening(wait_for_stop=False)
                # Restaurar valores de pausa originales
                self.recognizer.pause_threshold = 0.6
                self.recognizer.non_speaking_duration = 0.5

        return " ".join(final_text).strip()

    def transcribe_file(self, filepath: str) -> str:
        """
        Transcribe un archivo de audio local.

        Args:
            filepath: Ruta absoluta al archivo de audio (.mp3, .wav, .m4a, etc.).

        Returns:
            Texto transcrito completo.

        Raises:
            APIVoiceException: Si el archivo no existe.
        """
        if not os.path.exists(filepath):
            raise APIVoiceException(f"Archivo de audio no encontrado: {filepath}")
        logger.info("Transcribiendo archivo: %s", filepath)
        print(f"⏳ Transcribiendo archivo: {filepath}...")
        return self._do_transcribe(filepath)
