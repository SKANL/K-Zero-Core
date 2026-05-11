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


def resolve_toolset(name: str, visited: set[str] | None = None) -> list[Callable]:
    """Resuelve un toolset a callables, preservando orden y evitando ciclos."""
    if visited is None:
        visited = set()
    if name in visited:
        return []
    visited.add(name)

    resolved: list[Callable] = []
    by_name = {spec.name: spec.func for spec in get_tool_specs()}
    for item in TOOLSETS.get(name, ()):
        if item in TOOLSETS:
            resolved.extend(resolve_toolset(item, visited))
        elif item in by_name:
            resolved.append(by_name[item])

    deduped: list[Callable] = []
    seen: set[str] = set()
    for tool in resolved:
        tool_name = getattr(tool, "__name__", "")
        if tool_name and tool_name not in seen:
            seen.add(tool_name)
            deduped.append(tool)
    return deduped


def resolve_toolset_specs(name: str, visited: set[str] | None = None) -> list[ToolSpec]:
    """Resuelve un toolset a ToolSpec, preservando orden y evitando ciclos."""
    if visited is None:
        visited = set()
    if name in visited:
        return []
    visited.add(name)

    resolved: list[ToolSpec] = []
    by_name = {spec.name: spec for spec in get_tool_specs()}
    for item in TOOLSETS.get(name, ()):
        if item in TOOLSETS:
            resolved.extend(resolve_toolset_specs(item, visited))
        elif item in by_name:
            resolved.append(by_name[item])

    deduped: list[ToolSpec] = []
    seen: set[str] = set()
    for spec in resolved:
        if spec.name not in seen:
            seen.add(spec.name)
            deduped.append(spec)
    return deduped
