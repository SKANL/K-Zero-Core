"""
Módulo de enumeración de fuentes de audio disponibles en el sistema.

Provee:
    get_audio_devices       : Lista micrófonos y dispositivos loopback WASAPI.
    get_running_applications: Lista procesos activos con ventana (para futuros inyectores).
"""

import logging

import psutil

logger = logging.getLogger(__name__)

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    pyaudio = None

# Procesos del sistema operativo que no son aplicaciones de usuario
_OS_PROCESSES = frozenset({
    "svchost", "system", "registry", "smss", "csrss",
    "wininit", "services", "lsass", "conhost",
})


def get_audio_devices() -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """
    Enumera los dispositivos de audio disponibles usando la API WASAPI de Windows.

    Separa los dispositivos en micrófonos (entrada estándar) y dispositivos loopback
    (captura del audio que el sistema está reproduciendo, útil para grabar reuniones).

    Returns:
        Tupla (mics, loopbacks) donde cada elemento es una lista de
        (device_index, device_name). Ambas listas vacías si pyaudiowpatch
        no está instalado o no se pueden enumerar dispositivos.
    """
    if not pyaudio:
        logger.warning(
            "pyaudiowpatch no está instalado. No se pueden enumerar dispositivos WASAPI. "
            "Instálalo con: uv pip install PyAudioWPatch"
        )
        return [], []

    p = pyaudio.PyAudio()
    mics: list[tuple[int, str]] = []
    loopbacks: list[tuple[int, str]] = []

    try:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)

        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev["hostApi"] != wasapi_info["index"]:
                continue

            if dev.get("isLoopbackDevice", False):
                loopbacks.append((i, dev["name"]))
            elif dev["maxInputChannels"] > 0:
                mics.append((i, dev["name"]))

    except Exception as e:
        logger.error("Error enumerando dispositivos de audio WASAPI: %s", e)
    finally:
        p.terminate()

    return mics, loopbacks


def get_running_applications() -> list[dict]:
    """
    Lista las aplicaciones de usuario en ejecución (procesos con nombre .exe).

    Filtra procesos del sistema operativo y devuelve una lista deduplicada,
    ordenada por nombre. Útil para futuros inyectores de Process Loopback nativos.

    Returns:
        Lista de diccionarios con claves 'name' (str) y 'pid' (int),
        ordenada alfabéticamente por nombre.
    """
    unique_apps: dict[str, int] = {}

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name: str = proc.info["name"] or ""
            if name.endswith(".exe"):
                name = name[:-4]
            if name and name.lower() not in _OS_PROCESSES and name not in unique_apps:
                unique_apps[name] = proc.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return [{"name": k, "pid": v} for k, v in sorted(unique_apps.items())]
