"""Helpers compartidos para tools documentales."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from k_zero_core.core.config import DATA_DIR
from k_zero_core.core.tool_safety import resolve_safe_path
from k_zero_core.services.design_md import (
    clean_inline_text,
    extract_urls,
    parse_markdown_blocks,
)


EXPORTS_DIR = DATA_DIR / "exports"
DEFAULT_MAX_FRONTEND_FILES = 30
FRONTEND_EXTENSIONS = {".html", ".css", ".js", ".jsx", ".ts", ".tsx"}


def set_exports_dir(path: Path) -> None:
    """Actualiza el directorio de exports usado por todos los renderers documentales."""
    global EXPORTS_DIR
    EXPORTS_DIR = path


def _export_path(name: str, suffix: str) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    clean = "".join(char for char in name if char.isalnum() or char in ("-", "_")).strip() or "entregable"
    if not suffix.startswith("."):
        suffix = "." + suffix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return EXPORTS_DIR / f"{clean}_{timestamp}{suffix}"


def _read_text_like(path: Path, max_chars: int) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:max_chars] + ("\n[...truncado...]" if len(text) > max_chars else "")


def _created_result(path: Path, output_type: str, suggested_name: str) -> str:
    return (
        f"Archivo creado: {path}\n"
        f"Tipo: {output_type}\n"
        f"Nombre sugerido: {suggested_name}\n"
        "Estado: creado"
    )


def _theme_color(deliverable: dict[str, Any], token_path: str, fallback: str) -> str:
    design = deliverable["design"]
    value = design.token(token_path, fallback)
    return value if isinstance(value, str) and value.startswith("#") else fallback


def _hex_rgb(hex_color: str) -> tuple[int, int, int]:
    clean = hex_color.strip().lstrip("#")
    return tuple(int(clean[index : index + 2], 16) for index in (0, 2, 4))


def _first_heading(blocks: list[dict[str, Any]], default: str) -> str:
    return next(
        (block["text"] for block in blocks if block["type"] == "heading" and block.get("level") == 1),
        default,
    )


def _table_rows(block: dict[str, Any]) -> list[list[str]]:
    return [block["headers"], *block["rows"]]


def _rows_from_json_or_markdown(datos: str) -> tuple[list[str], list[list[Any]], list[str]]:
    sources: list[str] = []
    try:
        parsed = json.loads(datos)
        rows = parsed if isinstance(parsed, list) else [parsed]
        if rows and isinstance(rows[0], dict):
            headers = list(rows[0].keys())
            return headers, [[row.get(header) for header in headers] for row in rows], sources
        normalized = [row if isinstance(row, list) else [row] for row in rows]
        width = max((len(row) for row in normalized), default=1)
        return [f"Columna {index}" for index in range(1, width + 1)], normalized, sources
    except Exception:
        blocks = parse_markdown_blocks(datos)
        sources = extract_urls(datos)
        for block in blocks:
            if block["type"] == "table":
                return block["headers"], block["rows"], sources
        extracted = [[block.get("type", ""), block.get("text", "")] for block in blocks if block.get("text")]
        return ["Tipo", "Contenido"], extracted or [["texto", clean_inline_text(datos)]], sources


def analizar_archivos_frontend(path: str, max_chars: int = 12000) -> str:
    """Revisa archivos HTML/CSS/JS locales y resume hallazgos de interfaz."""
    try:
        resolved = resolve_safe_path(path)
        files = [resolved] if resolved.is_file() else [
            file for file in resolved.rglob("*") if file.suffix.lower() in FRONTEND_EXTENSIONS
        ][:DEFAULT_MAX_FRONTEND_FILES]
        lines = [f"Archivos frontend analizados: {len(files)}"]
        for file in files:
            text = file.read_text(encoding="utf-8", errors="replace")
            lines.append(f"\nArchivo: {file}")
            lines.append(f"- Tamaño: {len(text)} caracteres")
            lines.append(f"- Usa forms: {'<form' in text.lower()}")
            lines.append(f"- Tiene alt=: {'alt=' in text.lower()}")
            lines.append(text[:800])
        return "\n".join(lines)[:max_chars]
    except Exception as exc:
        return f"Error al analizar frontend: {exc}"


def validar_entregable(texto: str, requisitos: str) -> str:
    """Valida de forma simple si un texto cumple requisitos explícitos."""
    missing = [
        requirement
        for raw in requisitos.replace(";", "\n").splitlines()
        if (requirement := raw.strip("- ").strip()) and requirement.lower() not in texto.lower()
    ]
    warnings = (
        ["El entregable parece contener Markdown crudo visible; usa limpiar_markdown_entregable o render nativo."]
        if "**" in texto or "###" in texto or any(line.strip().startswith("|") for line in texto.splitlines())
        else []
    )
    if not missing and not warnings:
        return "Validación: cumple los requisitos explícitos revisados."
    lines = ["Validación:"]
    if missing:
        lines.append("Faltan posibles requisitos:")
        lines.extend(f"- {item}" for item in missing[:20])
    if warnings:
        lines.append("Advertencias de formato:")
        lines.extend(f"- {item}" for item in warnings)
    return "\n".join(lines)
