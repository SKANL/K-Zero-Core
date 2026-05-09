"""Control de resultados grandes producidos por tools."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from k_zero_core.core.config import DATA_DIR


DEFAULT_MAX_INLINE_CHARS = 20_000
ARTIFACTS_DIR = DATA_DIR / "artifacts" / "tool-results"


def _configured_max_inline_chars() -> int:
    raw_value = os.getenv("K_ZERO_MAX_INLINE_TOOL_RESULT_CHARS", "")
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_MAX_INLINE_CHARS
    return value if value > 0 else DEFAULT_MAX_INLINE_CHARS


def prepare_tool_result(
    result: object,
    *,
    max_inline_chars: int | None = None,
    artifact_dir: Path | None = None,
) -> str:
    """
    Retorna un resultado de tool seguro para insertar en el historial.

    Los resultados cortos se dejan inline. Los resultados grandes se persisten
    como artefactos locales para evitar contaminar el contexto del modelo.
    """
    text = str(result)
    limit = max_inline_chars if max_inline_chars is not None else _configured_max_inline_chars()
    if len(text) <= limit:
        return text

    target_dir = artifact_dir or ARTIFACTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / f"tool-result-{uuid.uuid4().hex}.txt"
    file_path.write_text(text, encoding="utf-8")
    return (
        "Resultado demasiado grande para insertarlo completo en el contexto "
        f"({len(text):,} caracteres). Se guardó en: {file_path}"
    )
