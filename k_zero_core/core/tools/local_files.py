"""Tools generales para inspección segura de archivos y proyectos locales."""
from __future__ import annotations

import fnmatch
from datetime import datetime
from pathlib import Path

from k_zero_core.core.tool_safety import resolve_safe_path


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def leer_metadatos_archivo(path: str) -> str:
    """Lee metadatos básicos de un archivo local sin abrir su contenido completo."""
    try:
        resolved = resolve_safe_path(path)
    except ValueError as exc:
        return f"Error: {exc}"
    if not resolved.exists():
        return f"Error: '{resolved}' no existe."
    stat = resolved.stat()
    tipo = "directorio" if resolved.is_dir() else "archivo"
    return "\n".join(
        [
            f"Nombre: {resolved.name}",
            f"Ruta: {resolved}",
            f"Tipo: {tipo}",
            f"Extensión: {resolved.suffix.lower() or '(sin extensión)'}",
            f"Tamaño: {_format_size(stat.st_size)}",
            f"Modificado: {datetime.fromtimestamp(stat.st_mtime).isoformat(timespec='seconds')}",
        ]
    )


def buscar_archivos_locales(nombre_o_patron: str, root: str = ".", extensiones: str = "") -> str:
    """Busca archivos por nombre/patrón y extensiones dentro de una carpeta segura."""
    try:
        resolved_root = resolve_safe_path(root)
    except ValueError as exc:
        return f"Error: {exc}"
    if not resolved_root.exists() or not resolved_root.is_dir():
        return f"Error: '{resolved_root}' no es un directorio válido."

    allowed_exts = {
        ext.strip().lower() if ext.strip().startswith(".") else f".{ext.strip().lower()}"
        for ext in extensiones.split(",")
        if ext.strip()
    }
    pattern = nombre_o_patron.strip() or "*"
    matches: list[Path] = []
    for path in resolved_root.rglob("*"):
        if not path.is_file():
            continue
        if allowed_exts and path.suffix.lower() not in allowed_exts:
            continue
        if fnmatch.fnmatch(path.name.lower(), pattern.lower()) or pattern.lower() in path.name.lower():
            matches.append(path)
        if len(matches) >= 50:
            break

    if not matches:
        return "No se encontraron archivos."
    return "Archivos encontrados:\n" + "\n".join(f"- {path}" for path in matches)


def inspeccionar_proyecto(path: str = ".") -> str:
    """Resume estructura y archivos clave de un proyecto local."""
    try:
        root = resolve_safe_path(path)
    except ValueError as exc:
        return f"Error: {exc}"
    if not root.exists() or not root.is_dir():
        return f"Error: '{root}' no es un directorio válido."

    key_files = [
        "pyproject.toml",
        "requirements.txt",
        "package.json",
        "tsconfig.json",
        "README.md",
        "go.mod",
        "Cargo.toml",
    ]
    present = [name for name in key_files if (root / name).exists()]
    top_dirs = [entry.name for entry in sorted(root.iterdir()) if entry.is_dir() and not entry.name.startswith(".")][:20]
    top_files = [entry.name for entry in sorted(root.iterdir()) if entry.is_file()][:20]
    return "\n".join(
        [
            f"Proyecto: {root}",
            "Archivos clave: " + (", ".join(present) if present else "no detectados"),
            "Carpetas principales: " + (", ".join(top_dirs) if top_dirs else "ninguna"),
            "Archivos raíz: " + (", ".join(top_files) if top_files else "ninguno"),
        ]
    )
