"""Fachada pública de tools documentales.

Las implementaciones viven en módulos por formato para mantener responsabilidades
pequeñas sin romper imports existentes desde `k_zero_core.core.tools.documents`.
"""
from __future__ import annotations

from pathlib import Path

from k_zero_core.core.config import DATA_DIR
from k_zero_core.core.tool_safety import resolve_safe_path
from k_zero_core.core.tools import document_common as _common
from k_zero_core.core.tools.document_common import (
    _read_text_like,
    analizar_archivos_frontend as _analizar_archivos_frontend,
    validar_entregable as _validar_entregable,
)
from k_zero_core.core.tools.document_docx import (
    analizar_docx as _analizar_docx,
    crear_docx as _crear_docx,
    editar_docx_copia as _editar_docx_copia,
)
from k_zero_core.core.tools.document_pdf import (
    analizar_pdf as _analizar_pdf,
    combinar_pdf_copia as _combinar_pdf_copia,
    crear_pdf as _crear_pdf,
    dividir_pdf_copia as _dividir_pdf_copia,
    editar_pdf_copia as _editar_pdf_copia,
)
from k_zero_core.core.tools.document_presentations import (
    analizar_pptx as _analizar_pptx,
    crear_pptx as _crear_pptx,
    editar_pptx_copia as _editar_pptx_copia,
)
from k_zero_core.core.tools.document_spreadsheets import (
    analizar_xlsx as _analizar_xlsx,
    crear_xlsx as _crear_xlsx,
    editar_xlsx_copia as _editar_xlsx_copia,
)


EXPORTS_DIR = DATA_DIR / "exports"


def _sync_exports_dir() -> None:
    """Propaga parches legacy de documents.EXPORTS_DIR a los módulos extraídos."""
    _common.set_exports_dir(Path(EXPORTS_DIR))


def leer_archivo_inteligente(path: str, max_chars: int = 8000) -> str:
    """Lee un archivo local según su tipo y devuelve inventario + extracto."""
    try:
        resolved = resolve_safe_path(path)
    except ValueError as exc:
        return f"Error: {exc}"
    if not resolved.exists():
        return f"Error: '{resolved}' no existe."

    suffix = resolved.suffix.lower()
    if suffix == ".docx":
        return analizar_docx(str(resolved), max_chars=max_chars)
    if suffix == ".pdf":
        return analizar_pdf(str(resolved), max_chars=max_chars)
    if suffix in {".xlsx", ".xlsm", ".csv", ".tsv"}:
        return analizar_xlsx(str(resolved), max_rows=20)
    if suffix == ".pptx":
        return analizar_pptx(str(resolved), max_chars=max_chars)
    return f"Archivo: {resolved}\nTipo: {suffix or 'texto'}\n\n{_read_text_like(resolved, max_chars)}"


def analizar_docx(path: str, max_chars: int = 12000) -> str:
    _sync_exports_dir()
    return _analizar_docx(path, max_chars=max_chars)


def crear_docx(contenido_markdown: str, nombre_sugerido: str = "documento", design_md_path: str = "") -> str:
    _sync_exports_dir()
    return _crear_docx(contenido_markdown, nombre_sugerido, design_md_path)


def editar_docx_copia(path: str, instrucciones: str) -> str:
    _sync_exports_dir()
    return _editar_docx_copia(path, instrucciones)


def analizar_pdf(path: str, max_chars: int = 12000) -> str:
    _sync_exports_dir()
    return _analizar_pdf(path, max_chars=max_chars)


def crear_pdf(contenido_markdown: str, nombre_sugerido: str = "documento", design_md_path: str = "") -> str:
    _sync_exports_dir()
    return _crear_pdf(contenido_markdown, nombre_sugerido, design_md_path)


def editar_pdf_copia(path: str, instrucciones: str) -> str:
    _sync_exports_dir()
    return _editar_pdf_copia(path, instrucciones)


def dividir_pdf_copia(path: str, paginas: str) -> str:
    _sync_exports_dir()
    return _dividir_pdf_copia(path, paginas)


def combinar_pdf_copia(paths: str, nombre_sugerido: str = "pdf_combinado") -> str:
    _sync_exports_dir()
    return _combinar_pdf_copia(paths, nombre_sugerido)


def analizar_xlsx(path: str, max_rows: int = 20) -> str:
    _sync_exports_dir()
    return _analizar_xlsx(path, max_rows=max_rows)


def crear_xlsx(datos: str, nombre_sugerido: str = "datos", design_md_path: str = "") -> str:
    _sync_exports_dir()
    return _crear_xlsx(datos, nombre_sugerido, design_md_path)


def editar_xlsx_copia(path: str, instrucciones: str) -> str:
    _sync_exports_dir()
    return _editar_xlsx_copia(path, instrucciones)


def analizar_pptx(path: str, max_chars: int = 12000) -> str:
    _sync_exports_dir()
    return _analizar_pptx(path, max_chars=max_chars)


def crear_pptx(contenido_markdown: str, nombre_sugerido: str = "presentacion", design_md_path: str = "") -> str:
    _sync_exports_dir()
    return _crear_pptx(contenido_markdown, nombre_sugerido, design_md_path)


def editar_pptx_copia(path: str, instrucciones: str) -> str:
    _sync_exports_dir()
    return _editar_pptx_copia(path, instrucciones)


def analizar_archivos_frontend(path: str, max_chars: int = 12000) -> str:
    _sync_exports_dir()
    return _analizar_archivos_frontend(path, max_chars=max_chars)


def validar_entregable(texto: str, requisitos: str) -> str:
    return _validar_entregable(texto, requisitos)
