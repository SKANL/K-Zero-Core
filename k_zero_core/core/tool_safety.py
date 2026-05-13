"""Validaciones ligeras de seguridad para tools locales."""
from __future__ import annotations

import os
from pathlib import Path


def _configured_safe_roots() -> list[Path]:
    raw_roots = os.getenv("K_ZERO_SAFE_PATH_ROOTS", "")
    return [
        Path(candidate).expanduser().resolve()
        for raw in raw_roots.split(os.pathsep)
        if (candidate := raw.strip())
    ]


def resolve_safe_path(path_value: str | Path) -> Path:
    """
    Resuelve una ruta y aplica containment solo si K_ZERO_SAFE_PATH_ROOTS existe.

    El comportamiento histórico se preserva por defecto. El modo restringido es
    opt-in para usuarios que quieran limitar tools de filesystem a raíces
    explícitas.
    """
    raw = str(path_value)
    if "\x00" in raw:
        raise ValueError("La ruta contiene bytes nulos.")

    resolved = Path(raw).expanduser().resolve()
    safe_roots = _configured_safe_roots()
    if not safe_roots:
        return resolved

    for root in safe_roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue

    allowed = ", ".join(str(root) for root in safe_roots)
    raise ValueError(f"La ruta '{resolved}' está fuera de K_ZERO_SAFE_PATH_ROOTS ({allowed}).")
