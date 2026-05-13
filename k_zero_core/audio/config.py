"""
Configuración centralizada para el módulo de audio.

Todos los parámetros de STT (Whisper) y TTS (edge-tts / pygame) se definen
aquí como dataclasses con valores por defecto legibles desde variables de entorno.
Esto permite ajustar el comportamiento sin modificar código fuente.

Variables de entorno soportadas:
    STT_MODEL_SIZE       Tamaño del modelo Whisper (tiny/base/small/medium/large-v3). Default: small
    STT_LANGUAGE         Idioma de transcripción (es/en/None=autodetect). Default: es
    STT_VAD_THRESHOLD    Sensibilidad del VAD (0.0-1.0). Mayor valor = más estricto. Default: 0.5
    STT_ENERGY_THRESHOLD Umbral de energía de SpeechRecognition. Default: 300
    TTS_VOICE            ID de voz de edge-tts. Default: es-MX-DaliaNeural
"""

import os
from dataclasses import dataclass


@dataclass
class WhisperConfig:
    """
    Parámetros de transcripción para faster-whisper.

    Se instancia desde `from_env()` para leer configuración dinámica, o bien
    directamente con valores explícitos para pruebas y casos especiales.
    """

    model_size: str = "small"
    """Tamaño del modelo. 'small' ofrece buen balance precisión/velocidad en CPU."""

    language: str | None = "es"
    """Código de idioma ISO-639-1. None activa la autodetección (mayor latencia)."""

    device: str | None = None
    """
    Dispositivo de inferencia: 'cuda', 'cpu'. None activa la autodetección:
    usa CUDA si torch está disponible, CPU en caso contrario.
    """

    beam_size: int = 5
    """Número de hipótesis en beam search. Mayor = más preciso, más lento."""

    best_of: int = 5
    """Candidatos evaluados al usar temperatura > 0. Debe ser >= beam_size."""

    temperature: tuple[float, ...] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
    """
    Secuencia de temperaturas de fallback. Whisper prueba en orden ascendente
    si la transcripción actual supera los umbrales de compression_ratio o log_prob.
    Evita que el modelo se quede atascado en greedy decoding generando alucinaciones.
    """

    # --- Parámetros de calidad / filtros de alucinaciones ---
    compression_ratio_threshold: float = 2.4
    """Reintentar con mayor temperatura si la razón de compresión supera este valor."""

    log_prob_threshold: float = -1.0
    """Reintentar si la log-probabilidad media del segmento está por debajo de este umbral."""

    no_speech_threshold: float = 0.6
    """Descartar segmento si la probabilidad de 'no hay voz' supera este valor."""

    condition_on_previous_text: bool = False
    """
    Desactivado para evitar el bucle de alucinaciones donde el modelo copia
    la transcripción anterior en silencio ('¿Cómo estás? ¿Cómo estás?').
    """

    # --- Parámetros VAD (Voice Activity Detection) ---
    vad_filter: bool = True
    """Activar el filtro VAD de Silero para eliminar segmentos sin voz."""

    vad_threshold: float = 0.5
    """
    Umbral de probabilidad de voz del VAD (0.0-1.0).
    0.5 es el valor óptimo recomendado por Silero. Aumentar para entornos ruidosos.
    """

    min_speech_duration_ms: int = 250
    """Duración mínima en ms para considerar un chunk como voz real."""

    min_silence_duration_ms: int = 600
    """Duración mínima de silencio en ms para cortar entre segmentos."""

    max_speech_duration_s: float = 30.0
    """Duración máxima de un segmento de voz antes de forzar un corte."""

    speech_pad_ms: int = 300
    """Padding en ms alrededor de cada segmento de voz detectado."""

    # --- SpeechRecognition ---
    energy_threshold: int = 300
    """Umbral de energía de pyaudio. Valores más bajos = más sensible al ruido."""

    @classmethod
    def from_env(cls) -> "WhisperConfig":
        """
        Construye una instancia leyendo los valores desde variables de entorno.
        Los valores por defecto del dataclass se usan si la variable no está definida.
        """
        language_env = os.getenv("STT_LANGUAGE", "es")
        # Permitir el valor especial "auto" como alias de None (autodetección)
        language = None if language_env.lower() in ("none", "auto", "") else language_env

        return cls(
            model_size=os.getenv("STT_MODEL_SIZE", cls.model_size),
            language=language,
            vad_threshold=float(os.getenv("STT_VAD_THRESHOLD", str(cls.vad_threshold))),
            energy_threshold=int(os.getenv("STT_ENERGY_THRESHOLD", str(cls.energy_threshold))),
        )

    def get_vad_parameters(self) -> dict:
        """Retorna el diccionario de parámetros VAD listo para pasar a model.transcribe()."""
        return {
            "threshold": self.vad_threshold,
            "min_speech_duration_ms": self.min_speech_duration_ms,
            "min_silence_duration_ms": self.min_silence_duration_ms,
            "max_speech_duration_s": self.max_speech_duration_s,
            "speech_pad_ms": self.speech_pad_ms,
        }


@dataclass
class TtsConfig:
    """Parámetros de síntesis de voz (edge-tts + pygame)."""

    voice: str = "es-MX-DaliaNeural"
    """ID de voz de Microsoft edge-tts. Ver lista completa con: edge-tts --list-voices"""

    @classmethod
    def from_env(cls) -> "TtsConfig":
        """Construye la configuración desde variables de entorno."""
        return cls(
            voice=os.getenv("TTS_VOICE", cls.voice),
        )
