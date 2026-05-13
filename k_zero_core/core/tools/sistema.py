"""
Herramienta: Información del sistema operativo y hardware.
"""
import platform
import shutil
from pathlib import Path

import psutil


def informacion_sistema(detalle: str = "basico") -> str:
    """
    Obtiene información detallada sobre el sistema operativo y el hardware del usuario.

    Incluye: sistema operativo, versión, arquitectura del procesador, versión de Python,
    espacio en disco y directorio del usuario.

    Returns:
        Informe en texto con la información del sistema.
    """
    normalized = (detalle or "basico").strip().lower()
    if normalized not in {"basico", "hardware", "ollama", "disco", "todo"}:
        normalized = "basico"

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

    lineas.append(f"Sistema Operativo : {platform.system()} {platform.release()}")
    lineas.append(f"Versión SO        : {platform.version()}")
    lineas.append(f"Arquitectura      : {platform.machine()} ({platform.architecture()[0]})")

    procesador = platform.processor() or platform.uname().processor or "N/A"
    lineas.append(f"Procesador        : {procesador}")

    lineas.append(f"Python            : {platform.python_version()} ({platform.python_implementation()})")

    if normalized in {"basico", "disco", "todo"}:
        lineas.extend(_disk_lines())

    if normalized in {"hardware", "todo"}:
        lineas.extend(_hardware_lines())

    if normalized in {"ollama", "todo"}:
        lineas.extend(_ollama_lines())

    lineas.append(f"Directorio home   : {Path.home()}")

    lineas.append(f"Nombre del equipo  : {platform.node()}")

    return "\n".join(lineas)


def _disk_lines() -> list[str]:
    lineas: list[str] = []
    gigabyte = 1024 ** 3
    try:
        disco = shutil.disk_usage(Path.home())
        total_gb = disco.total / gigabyte
        used_gb = disco.used / gigabyte
        free_gb = disco.free / gigabyte
        uso_pct = (disco.used / disco.total) * 100
        lineas.append(
            f"Disco principal   : {used_gb:.1f} GB usados / {total_gb:.1f} GB totales "
            f"({free_gb:.1f} GB libres, {uso_pct:.0f}% ocupado)"
        )
    except Exception:
        lineas.append("Disco principal   : No disponible")
    return lineas


def _hardware_lines() -> list[str]:
    lineas: list[str] = []
    gigabyte = 1024 ** 3
    try:
        memory = psutil.virtual_memory()
        lineas.append(
            f"Memoria RAM       : {memory.available / gigabyte:.1f} GB libres / "
            f"{memory.total / gigabyte:.1f} GB totales ({memory.percent:.0f}% usada)"
        )
    except Exception:
        lineas.append("Memoria RAM       : No disponible")
    try:
        lineas.append(f"CPU núcleos       : {psutil.cpu_count(logical=False) or 'N/D'} físicos / {psutil.cpu_count()} lógicos")
    except Exception:
        lineas.append("CPU núcleos       : No disponible")
    lineas.append(f"GPU               : {_detect_gpu()}")
    return lineas


def _detect_gpu() -> str:
    try:
        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            return "No detectada por nvidia-smi"
        import subprocess

        completed = subprocess.run(
            [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return completed.stdout.strip() or "No disponible"
    except Exception:
        return "No disponible"


def _ollama_lines() -> list[str]:
    lineas = ["Ollama            : No disponible"]
    try:
        import ollama

        models = ollama.list().get("models", [])
        names = [model.get("model") or model.get("name", "") for model in models]
        lineas[0] = "Ollama            : Disponible"
        lineas.append("Modelos Ollama    : " + (", ".join(name for name in names if name) or "sin modelos listados"))
    except Exception as exc:
        lineas.append(f"Ollama detalle    : {exc}")
    return lineas
