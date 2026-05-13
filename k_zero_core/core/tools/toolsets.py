"""Toolsets declarativos para roles y modos."""
from __future__ import annotations

from collections.abc import Callable

from k_zero_core.core.tools import get_tool_specs
from k_zero_core.core.tools.registry import ToolSpec

TOOLSETS: dict[str, tuple[str, ...]] = {
    "research": (
        "buscar_en_internet",
        "buscar_tavily",
        "leer_pagina_web",
        "extraer_wikipedia",
        "buscar_en_documentos_locales",
    ),
    "analysis": ("analizar_valores_json", "calcular_matematica"),
    "filesystem_safe": (
        "leer_archivo",
        "listar_directorio",
        "buscar_archivos_locales",
        "inspeccionar_proyecto",
        "leer_metadatos_archivo",
    ),
    "system": ("informacion_sistema", "obtener_hora_actual"),
    "rag": ("buscar_en_documentos_locales",),
    "memory": ("memory",),
    "todo": ("todo",),
    "documents_read": (
        "validar_design_md",
        "previsualizar_estilo_entregable",
        "limpiar_markdown_entregable",
        "leer_archivo_inteligente",
        "analizar_docx",
        "analizar_pdf",
        "analizar_xlsx",
        "analizar_pptx",
    ),
    "documents_write": (
        "crear_design_md",
        "crear_docx",
        "editar_docx_copia",
        "crear_pdf",
        "editar_pdf_copia",
        "dividir_pdf_copia",
        "combinar_pdf_copia",
        "crear_xlsx",
        "editar_xlsx_copia",
        "crear_pptx",
        "editar_pptx_copia",
    ),
    "documents": ("documents_read", "documents_write"),
    "design": (
        "validar_design_md",
        "crear_design_md",
        "previsualizar_estilo_entregable",
        "limpiar_markdown_entregable",
    ),
    "frontend": ("analizar_archivos_frontend",),
    "validation": ("validar_entregable",),
    "director": ("research", "analysis", "filesystem_safe", "system", "rag", "documents", "design", "frontend", "validation"),
}


def _resolve_toolset_items(name: str, by_name: dict[str, object], visited: set[str] | None = None) -> list[object]:
    if visited is None:
        visited = set()
    if name in visited:
        return []
    visited.add(name)

    resolved: list[object] = []
    for item in TOOLSETS.get(name, ()):
        if item in TOOLSETS:
            resolved.extend(_resolve_toolset_items(item, by_name, visited))
        elif item in by_name:
            resolved.append(by_name[item])
    return resolved


def _dedupe_by_name(items: list[object]) -> list[object]:
    deduped: list[object] = []
    seen: set[str] = set()
    for item in items:
        item_name = getattr(item, "name", None) or getattr(item, "__name__", "")
        if item_name and item_name not in seen:
            seen.add(item_name)
            deduped.append(item)
    return deduped


def resolve_toolset(name: str, visited: set[str] | None = None) -> list[Callable]:
    """Resuelve un toolset a callables, preservando orden y evitando ciclos."""
    by_name = {spec.name: spec.func for spec in get_tool_specs()}
    return _dedupe_by_name(_resolve_toolset_items(name, by_name, visited))


def resolve_toolset_specs(name: str, visited: set[str] | None = None) -> list[ToolSpec]:
    """Resuelve un toolset a ToolSpec, preservando orden y evitando ciclos."""
    by_name = {spec.name: spec for spec in get_tool_specs()}
    return _dedupe_by_name(_resolve_toolset_items(name, by_name, visited))
