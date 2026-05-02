"""
Herramienta: Información del sistema operativo y hardware.
"""
import platform
import shutil
from pathlib import Path


def informacion_sistema() -> str:
    """
    Obtiene información detallada sobre el sistema operativo y el hardware del usuario.

    Incluye: sistema operativo, versión, arquitectura del procesador, versión de Python,
    espacio en disco y directorio del usuario.

    Returns:
        Informe en texto con la información del sistema.
    """
    lineas = ["=== Información del Sistema ===\n"]

    # Sistema Operativo
    lineas.append(f"Sistema Operativo : {platform.system()} {platform.release()}")
    lineas.append(f"Versión           : {platform.version()}")
    lineas.append(f"Arquitectura      : {platform.machine()} ({platform.architecture()[0]})")

    # Procesador
    procesador = platform.processor() or platform.uname().processor or "N/A"
    lineas.append(f"Procesador        : {procesador}")

    # Python
    lineas.append(f"Python            : {platform.python_version()} ({platform.python_implementation()})")

    # Disco principal
    try:
        disco = shutil.disk_usage(Path.home())
        total_gb = disco.total / (1024 ** 3)
        used_gb = disco.used / (1024 ** 3)
        free_gb = disco.free / (1024 ** 3)
        uso_pct = (disco.used / disco.total) * 100
        lineas.append(
            f"Disco principal   : {used_gb:.1f} GB usados / {total_gb:.1f} GB totales "
            f"({free_gb:.1f} GB libres, {uso_pct:.0f}% ocupado)"
        )
    except Exception:
        lineas.append("Disco principal   : No disponible")

    # Directorio del usuario
    lineas.append(f"Directorio home   : {Path.home()}")

    # Hostname
    lineas.append(f"Nombre del equipo  : {platform.node()}")

    return "\n".join(lineas)
