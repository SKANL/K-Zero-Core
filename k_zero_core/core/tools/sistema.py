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

    # K-Zero-Core (Metadata)
    try:
        import tomllib
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        pyproject_path = project_root / "pyproject.toml"
        if pyproject_path.is_file():
            with pyproject_path.open("rb") as f:
                metadata = tomllib.load(f)
                app_version = metadata.get("project", {}).get("version", "Desconocida")
                app_name = metadata.get("project", {}).get("name", "K-Zero-Core")
            lineas.append(f"Aplicación        : {app_name} (v{app_version})\n")
    except Exception:
        pass

    # Sistema Operativo
    lineas.append(f"Sistema Operativo : {platform.system()} {platform.release()}")
    lineas.append(f"Versión SO        : {platform.version()}")
    lineas.append(f"Arquitectura      : {platform.machine()} ({platform.architecture()[0]})")

    # Procesador
    procesador = platform.processor() or platform.uname().processor or "N/A"
    lineas.append(f"Procesador        : {procesador}")

    # Python
    lineas.append(f"Python            : {platform.python_version()} ({platform.python_implementation()})")

    # Constantes
    GIGABYTE = 1024 ** 3

    # Disco principal
    try:
        disco = shutil.disk_usage(Path.home())
        total_gb = disco.total / GIGABYTE
        used_gb = disco.used / GIGABYTE
        free_gb = disco.free / GIGABYTE
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
