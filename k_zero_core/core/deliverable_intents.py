"""Detección de intenciones de escritura de entregables."""
from __future__ import annotations

from typing import Any


DELIVERABLE_WRITE_TOOLS: dict[str, tuple[str, str]] = {
    "crear_docx": ("docx", "nombre_sugerido"),
    "crear_pdf": ("pdf", "nombre_sugerido"),
    "crear_xlsx": ("xlsx", "nombre_sugerido"),
    "crear_pptx": ("pptx", "nombre_sugerido"),
    "editar_docx_copia": ("docx", "path"),
    "editar_pdf_copia": ("pdf", "path"),
    "editar_xlsx_copia": ("xlsx", "path"),
    "editar_pptx_copia": ("pptx", "path"),
    "dividir_pdf_copia": ("pdf", "path"),
    "combinar_pdf_copia": ("pdf", "nombre_sugerido"),
    "crear_design_md": ("design.md", "nombre"),
}


def is_deliverable_write_tool(function_name: str) -> bool:
    """Indica si una tool escribe un entregable o una copia en exports."""
    return function_name in DELIVERABLE_WRITE_TOOLS


def deliverable_intent_key(function_name: str, arguments: dict[str, Any]) -> tuple[str, str] | None:
    """Normaliza tipo/nombre de salida para deduplicar escrituras repetidas."""
    if function_name not in DELIVERABLE_WRITE_TOOLS:
        return None
    output_type, argument_name = DELIVERABLE_WRITE_TOOLS[function_name]
    raw_name = str(arguments.get(argument_name) or arguments.get("nombre_sugerido") or function_name)
    normalized = raw_name.strip().lower().replace("\\", "/")
    return output_type, normalized
