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
from typing import List, Callable

from k_zero_core.core.tools.date_time import obtener_hora_actual
from k_zero_core.core.tools.matematica import calcular_matematica
from k_zero_core.core.tools.filesystem import leer_archivo, listar_directorio
from k_zero_core.core.tools.sistema import informacion_sistema
from k_zero_core.core.tools.analisis_json import analizar_valores_json
from k_zero_core.core.tools.web_search import buscar_en_internet, buscar_tavily
from k_zero_core.core.tools.web_reader import leer_pagina_web, extraer_wikipedia
from k_zero_core.core.tools.rag_search import buscar_en_documentos_locales

# Registro de todas las tools disponibles
# Para desactivar una tool, simplemente coméntala aquí
_ALL_TOOLS: List[Callable] = [
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
]


def get_all_tools() -> List[Callable]:
    """
    Retorna la lista de todas las herramientas disponibles para el Agente.

    Returns:
        Lista de funciones callable que el modelo puede invocar como tools.
    """
    return list(_ALL_TOOLS)

