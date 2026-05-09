"""Helpers de orquestación para DirectorMode."""
from collections.abc import Callable
from typing import Dict, List

from k_zero_core.core.tools.analisis_json import analizar_valores_json
from k_zero_core.core.tools.date_time import obtener_hora_actual
from k_zero_core.core.tools.filesystem import leer_archivo, listar_directorio
from k_zero_core.core.tools.matematica import calcular_matematica
from k_zero_core.core.tools.rag_search import buscar_en_documentos_locales
from k_zero_core.core.tools.sistema import informacion_sistema
from k_zero_core.core.tools.web_reader import extraer_wikipedia, leer_pagina_web
from k_zero_core.core.tools.web_search import buscar_en_internet, buscar_tavily

RoleTools = Dict[str, List[Callable]]

ROLE_TOOLS: RoleTools = {
    "investigador": [
        buscar_en_internet,
        buscar_tavily,
        leer_pagina_web,
        extraer_wikipedia,
        buscar_en_documentos_locales,
    ],
    "analista": [analizar_valores_json, calcular_matematica],
    "tecnico": [leer_archivo, listar_directorio, informacion_sistema, obtener_hora_actual],
}

ROLE_LABELS = {
    "investigador": "Investigador",
    "analista": "Analista",
    "tecnico": "Técnico",
}

ROLE_RESULT_HEADERS = {
    "investigador": "DATOS DEL INVESTIGADOR",
    "analista": "DATOS DEL ANALISTA",
    "tecnico": "DATOS DEL TÉCNICO",
}


def build_classifier_prompt(user_text: str) -> str:
    """Construye el prompt usado por el Director para seleccionar especialistas."""
    return (
        f"La consulta del usuario es: '{user_text}'\n"
        "Selecciona CUALES de los siguientes especialistas necesitas invocar para recopilar datos.\n"
        "- investigador (busca en la web, extrae wikipedia, lee urls, busca en documentos).\n"
        "- analista (calcula matemáticas, extrae números de JSONs).\n"
        "- tecnico (lee archivos locales, lista carpetas, ve info del sistema/SO, hora).\n"
        "Responde ÚNICAMENTE con los nombres separados por coma en minúsculas (ej: investigador, tecnico). "
        "Si puedes responderlo directamente sin ayuda, responde: ninguno."
    )


def parse_roles(raw_roles: str) -> List[str]:
    """Normaliza la salida del clasificador a roles soportados y orden estable."""
    normalized = raw_roles.lower().replace("técnico", "tecnico")
    if "ninguno" in normalized:
        return []
    return [role for role in ROLE_TOOLS if role in normalized]


def build_director_context(sub_results: List[str]) -> str:
    """Construye el contexto privado que se agrega al turno del usuario."""
    if not sub_results:
        return ""
    return "\n\nAquí tienes la información recopilada por tu equipo:\n" + "\n\n".join(sub_results)
