"""
Registro central de herramientas (tools) disponibles para los modos de agente.

## Cómo agregar una nueva tool

1. Crea un archivo en este directorio: `k_zero_core/core/tools/mi_tool.py`
2. Define la función con type hints y un docstring claro (el SDK de Ollama lo parsea automáticamente).
3. Importa la función aquí y agrégala a `_ALL_TOOLS`.
4. ¡Listo! No necesitas modificar ningún otro archivo.

## Formato del docstring (Ollama lo usa para generar el schema de la tool)

    def mi_funcion(param: str) -> str:
        \"\"\"Descripción clara de qué hace la función.

        Args:
            param: Descripción del parámetro.

        Returns:
            Descripción de lo que retorna.
        \"\"\"
"""
from collections.abc import Callable

from k_zero_core.core.tools.date_time import obtener_hora_actual
from k_zero_core.core.tools.matematica import calcular_matematica
from k_zero_core.core.tools.filesystem import leer_archivo, listar_directorio
from k_zero_core.core.tools.sistema import informacion_sistema
from k_zero_core.core.tools.analisis_json import analizar_valores_json
from k_zero_core.core.tools.web_search import buscar_en_internet, buscar_tavily
from k_zero_core.core.tools.web_reader import leer_pagina_web, extraer_wikipedia
from k_zero_core.core.tools.rag_search import buscar_en_documentos_locales
from k_zero_core.core.tools.memory import memory
from k_zero_core.core.tools.todo import todo
from k_zero_core.core.tools.local_files import (
    buscar_archivos_locales,
    inspeccionar_proyecto,
    leer_metadatos_archivo,
)
from k_zero_core.core.tools.documents import (
    analizar_archivos_frontend,
    analizar_docx,
    analizar_pdf,
    analizar_pptx,
    analizar_xlsx,
    combinar_pdf_copia,
    crear_docx,
    crear_pdf,
    crear_pptx,
    crear_xlsx,
    dividir_pdf_copia,
    editar_docx_copia,
    editar_pdf_copia,
    editar_pptx_copia,
    editar_xlsx_copia,
    leer_archivo_inteligente,
    validar_entregable,
)
from k_zero_core.core.tools.design_md import (
    crear_design_md,
    limpiar_markdown_entregable,
    previsualizar_estilo_entregable,
    validar_design_md,
)
from k_zero_core.core.tools.registry import (
    ToolAudience,
    ToolCost,
    ToolPrivacy,
    ToolSpec,
    build_tool_specs,
)

_ALL_TOOLS: list[Callable] = [
    obtener_hora_actual,
    calcular_matematica,
    leer_archivo,
    listar_directorio,
    informacion_sistema,
    analizar_valores_json,
    buscar_en_internet,
    buscar_tavily,
    leer_pagina_web,
    extraer_wikipedia,
    buscar_en_documentos_locales,
    memory,
    todo,
    buscar_archivos_locales,
    inspeccionar_proyecto,
    leer_metadatos_archivo,
    leer_archivo_inteligente,
    analizar_docx,
    crear_docx,
    editar_docx_copia,
    analizar_pdf,
    crear_pdf,
    editar_pdf_copia,
    dividir_pdf_copia,
    combinar_pdf_copia,
    analizar_xlsx,
    crear_xlsx,
    editar_xlsx_copia,
    analizar_pptx,
    crear_pptx,
    editar_pptx_copia,
    analizar_archivos_frontend,
    validar_entregable,
    validar_design_md,
    crear_design_md,
    previsualizar_estilo_entregable,
    limpiar_markdown_entregable,
]


def get_all_tools() -> list[Callable]:
    """
    Retorna la lista de todas las herramientas disponibles para el Agente.

    Returns:
        Lista de funciones callable que el modelo puede invocar como tools.
    """
    return list(_ALL_TOOLS)


def get_tool_specs() -> list[ToolSpec]:
    """Retorna metadata de tools en el mismo orden de get_all_tools()."""
    return build_tool_specs(get_all_tools())


def get_available_tool_specs() -> list[ToolSpec]:
    """Retorna metadata de tools con dependencias de entorno satisfechas."""
    return [spec for spec in get_tool_specs() if spec.available]


def get_tools_by_capability(
    *,
    audience: ToolAudience | None = None,
    cost: ToolCost | None = None,
    privacy: ToolPrivacy | None = None,
    requires_network: bool | None = None,
    writes_files: bool | None = None,
) -> list[ToolSpec]:
    """Filtra ToolSpec por capacidades declarativas."""
    specs = get_tool_specs()
    if audience is not None:
        specs = [spec for spec in specs if spec.audience == audience]
    if cost is not None:
        specs = [spec for spec in specs if spec.cost == cost]
    if privacy is not None:
        specs = [spec for spec in specs if spec.privacy == privacy]
    if requires_network is not None:
        specs = [spec for spec in specs if spec.requires_network == requires_network]
    if writes_files is not None:
        specs = [spec for spec in specs if spec.writes_files == writes_files]
    return specs


def describe_tool_capabilities(spec: ToolSpec) -> str:
    """Devuelve una línea legible de costo, privacidad y permisos de una tool."""
    return (
        f"{spec.name}: audience={spec.audience.value}, cost={spec.cost.value}, "
        f"privacy={spec.privacy.value}, requires_network={spec.requires_network}, "
        f"writes_files={spec.writes_files}, permission={spec.permission.value}"
    )
