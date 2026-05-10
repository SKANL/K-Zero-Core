"""Metadata interna para tools sin romper el contrato de get_all_tools()."""
from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Type

from pydantic import BaseModel, ValidationError


class ToolPermission(StrEnum):
    """Nivel mínimo de permiso requerido para ejecutar una tool."""

    READ_ONLY = "read_only"
    WRITE_LOCAL = "write_local"
    ASK = "ask"
    DENY = "deny"


@dataclass(frozen=True)
class ToolSpec:
    """Describe una tool registrada en K-Zero."""

    name: str
    func: Callable
    description: str = ""
    requires_env: tuple[str, ...] = field(default_factory=tuple)
    permission: ToolPermission = ToolPermission.READ_ONLY
    args_schema: Type[BaseModel] | None = None
    toolset: str = "general"
    max_inline_chars: int | None = None

    @property
    def available(self) -> bool:
        return all(os.getenv(var) for var in self.requires_env)

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Valida argumentos con Pydantic cuando la tool declara schema."""
        if self.args_schema is None:
            return arguments
        model = self.args_schema.model_validate(arguments)
        return model.model_dump()

    def validation_error(self, arguments: dict[str, Any]) -> str | None:
        """Retorna mensaje de error legible si los argumentos no son válidos."""
        try:
            self.validate_arguments(arguments)
        except ValidationError as exc:
            return str(exc)
        return None

    def json_schema(self) -> dict[str, Any]:
        """Expone JSON Schema cuando hay schema declarado."""
        if self.args_schema is None:
            return {"type": "object", "properties": {}}
        return self.args_schema.model_json_schema()


TOOL_METADATA: dict[str, dict[str, Any]] = {
    "leer_archivo": {"toolset": "filesystem_safe", "permission": ToolPermission.READ_ONLY},
    "listar_directorio": {"toolset": "filesystem_safe", "permission": ToolPermission.READ_ONLY},
    "analizar_valores_json": {"toolset": "analysis", "permission": ToolPermission.READ_ONLY},
    "calcular_matematica": {"toolset": "analysis", "permission": ToolPermission.READ_ONLY},
    "buscar_en_internet": {"toolset": "research", "permission": ToolPermission.READ_ONLY},
    "buscar_tavily": {
        "toolset": "research",
        "permission": ToolPermission.READ_ONLY,
        "requires_env": ("TAVILY_API_KEY",),
    },
    "leer_pagina_web": {"toolset": "research", "permission": ToolPermission.READ_ONLY},
    "extraer_wikipedia": {"toolset": "research", "permission": ToolPermission.READ_ONLY},
    "buscar_en_documentos_locales": {"toolset": "rag", "permission": ToolPermission.READ_ONLY},
    "informacion_sistema": {"toolset": "system", "permission": ToolPermission.READ_ONLY},
    "obtener_hora_actual": {"toolset": "system", "permission": ToolPermission.READ_ONLY},
    "memory": {"toolset": "memory", "permission": ToolPermission.READ_ONLY},
    "todo": {"toolset": "todo", "permission": ToolPermission.READ_ONLY},
    "buscar_archivos_locales": {"toolset": "filesystem_safe", "permission": ToolPermission.READ_ONLY},
    "inspeccionar_proyecto": {"toolset": "filesystem_safe", "permission": ToolPermission.READ_ONLY},
    "leer_metadatos_archivo": {"toolset": "filesystem_safe", "permission": ToolPermission.READ_ONLY},
    "leer_archivo_inteligente": {"toolset": "documents", "permission": ToolPermission.READ_ONLY},
    "analizar_docx": {"toolset": "documents", "permission": ToolPermission.READ_ONLY},
    "crear_docx": {"toolset": "documents", "permission": ToolPermission.WRITE_LOCAL},
    "editar_docx_copia": {"toolset": "documents", "permission": ToolPermission.WRITE_LOCAL},
    "analizar_pdf": {"toolset": "documents", "permission": ToolPermission.READ_ONLY},
    "crear_pdf": {"toolset": "documents", "permission": ToolPermission.WRITE_LOCAL},
    "editar_pdf_copia": {"toolset": "documents", "permission": ToolPermission.WRITE_LOCAL},
    "dividir_pdf_copia": {"toolset": "documents", "permission": ToolPermission.WRITE_LOCAL},
    "combinar_pdf_copia": {"toolset": "documents", "permission": ToolPermission.WRITE_LOCAL},
    "analizar_xlsx": {"toolset": "documents", "permission": ToolPermission.READ_ONLY},
    "crear_xlsx": {"toolset": "documents", "permission": ToolPermission.WRITE_LOCAL},
    "editar_xlsx_copia": {"toolset": "documents", "permission": ToolPermission.WRITE_LOCAL},
    "analizar_pptx": {"toolset": "documents", "permission": ToolPermission.READ_ONLY},
    "crear_pptx": {"toolset": "documents", "permission": ToolPermission.WRITE_LOCAL},
    "editar_pptx_copia": {"toolset": "documents", "permission": ToolPermission.WRITE_LOCAL},
    "analizar_archivos_frontend": {"toolset": "frontend", "permission": ToolPermission.READ_ONLY},
    "validar_entregable": {"toolset": "validation", "permission": ToolPermission.READ_ONLY},
    "validar_design_md": {"toolset": "design", "permission": ToolPermission.READ_ONLY},
    "crear_design_md": {"toolset": "design", "permission": ToolPermission.WRITE_LOCAL},
    "previsualizar_estilo_entregable": {"toolset": "design", "permission": ToolPermission.READ_ONLY},
    "limpiar_markdown_entregable": {"toolset": "design", "permission": ToolPermission.READ_ONLY},
}


def build_tool_specs(tools: list[Callable]) -> list[ToolSpec]:
    """Construye metadata en el mismo orden que la lista pública de callables."""
    specs: list[ToolSpec] = []
    for tool in tools:
        metadata = TOOL_METADATA.get(tool.__name__, {})
        specs.append(
            ToolSpec(
                name=tool.__name__,
                func=tool,
                description=(tool.__doc__ or "").strip().splitlines()[0] if tool.__doc__ else "",
                requires_env=metadata.get("requires_env", ()),
                permission=metadata.get("permission", ToolPermission.READ_ONLY),
                args_schema=metadata.get("args_schema"),
                toolset=metadata.get("toolset", "general"),
                max_inline_chars=metadata.get("max_inline_chars"),
            )
        )
    return specs
