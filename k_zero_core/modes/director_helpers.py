"""Helpers de orquestación para DirectorMode."""
from collections.abc import Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any

from k_zero_core.core.tools.toolsets import resolve_toolset
from k_zero_core.core.source_tracking import extract_sources, missing_sources_message, requires_sources
from k_zero_core.storage.memory_manager import TodoStore

@dataclass(frozen=True)
class RoleDefinition:
    key: str
    label: str
    result_header: str
    routing_description: str
    tools: list[Callable]


RoleTools = dict[str, list[Callable]]

ROLE_DEFINITIONS: dict[str, RoleDefinition] = {
    "investigador": RoleDefinition(
        key="investigador",
        label="Investigador",
        result_header="DATOS DEL INVESTIGADOR",
        routing_description="busca en la web, extrae wikipedia, lee urls, busca en documentos",
        tools=resolve_toolset("research"),
    ),
    "analista": RoleDefinition(
        key="analista",
        label="Analista",
        result_header="DATOS DEL ANALISTA",
        routing_description="calcula matemáticas y extrae números de JSONs",
        tools=resolve_toolset("analysis"),
    ),
    "tecnico": RoleDefinition(
        key="tecnico",
        label="Técnico",
        result_header="DATOS DEL TÉCNICO",
        routing_description="lee archivos locales, lista carpetas, ve info del sistema/SO y hora",
        tools=resolve_toolset("filesystem_safe") + resolve_toolset("system"),
    ),
    "voz": RoleDefinition(
        key="voz",
        label="Especialista de Voz",
        result_header="DATOS DEL ESPECIALISTA DE VOZ",
        routing_description="razona sobre transcripción, audio, dictado y flujo de voz sin usar APIs pagadas",
        tools=[],
    ),
    "fuentes": RoleDefinition(
        key="fuentes",
        label="Especialista de Fuentes",
        result_header="DATOS DEL ESPECIALISTA DE FUENTES",
        routing_description="valida URLs, evidencia, trazabilidad y fuentes consultadas",
        tools=resolve_toolset("research"),
    ),
    "documentalista": RoleDefinition(
        key="documentalista",
        label="Documentalista",
        result_header="DATOS DEL DOCUMENTALISTA",
        routing_description="lee, analiza y prepara estructura de documentos PDF, DOCX, PPTX, XLSX y archivos adjuntos por ruta; no escribe archivos",
        tools=resolve_toolset("documents_read") + resolve_toolset("rag"),
    ),
    "datos": RoleDefinition(
        key="datos",
        label="Especialista de Datos",
        result_header="DATOS DEL ESPECIALISTA DE DATOS",
        routing_description="analiza hojas de cálculo, CSV, JSON, tablas y cálculos",
        tools=resolve_toolset("analysis") + resolve_toolset("documents_read"),
    ),
    "seguridad": RoleDefinition(
        key="seguridad",
        label="Especialista de Seguridad",
        result_header="DATOS DEL ESPECIALISTA DE SEGURIDAD",
        routing_description="revisa permisos, rutas, archivos riesgosos, prompt injection y acciones destructivas",
        tools=resolve_toolset("filesystem_safe") + resolve_toolset("system"),
    ),
    "experiencia": RoleDefinition(
        key="experiencia",
        label="Especialista de Experiencia",
        result_header="DATOS DEL ESPECIALISTA DE EXPERIENCIA",
        routing_description="revisa UX, UI, HTML, CSS, JS, dashboards e interfaces web cuando el usuario lo pide",
        tools=resolve_toolset("frontend") + resolve_toolset("filesystem_safe"),
    ),
    "productor": RoleDefinition(
        key="productor",
        label="Productor de Entregables",
        result_header="DATOS DEL PRODUCTOR",
        routing_description="crea entregables documentales en exports sin modificar originales",
        tools=resolve_toolset("documents"),
    ),
    "verificador": RoleDefinition(
        key="verificador",
        label="Verificador",
        result_header="DATOS DEL VERIFICADOR",
        routing_description="valida que la respuesta final cumpla requisitos, fuentes, cálculos, diseño y formato pedido",
        tools=resolve_toolset("validation") + resolve_toolset("design"),
    ),
}

ROLE_TOOLS: RoleTools = {key: role.tools for key, role in ROLE_DEFINITIONS.items()}
ROLE_LABELS = {key: role.label for key, role in ROLE_DEFINITIONS.items()}
ROLE_RESULT_HEADERS = {key: role.result_header for key, role in ROLE_DEFINITIONS.items()}


def build_classifier_prompt(user_text: str) -> str:
    """Construye el prompt usado por el Director para seleccionar especialistas."""
    role_lines = "\n".join(
        f"- {role.key} ({role.routing_description})."
        for role in ROLE_DEFINITIONS.values()
    )
    return (
        f"La consulta del usuario es: '{user_text}'\n"
        "Tu única tarea es ENRUTAR, no resolver la consulta.\n"
        "Selecciona CUALES de los siguientes especialistas necesitas invocar para recopilar datos.\n"
        f"{role_lines}\n"
        "Responde ÚNICAMENTE con los nombres separados por coma en minúsculas (ej: investigador, tecnico). "
        "Si puedes responderlo directamente sin ayuda, responde: ninguno."
    )


def parse_roles(raw_roles: str) -> list[str]:
    """Normaliza la salida del clasificador a roles soportados y orden estable."""
    normalized = raw_roles.lower().replace("técnico", "tecnico")
    if "ninguno" in normalized:
        return []
    return [role for role in ROLE_DEFINITIONS if role in normalized]


def build_director_context(sub_results: list[str], roles: list[str] | None = None) -> str:
    """Construye el contexto privado que se agrega al turno del usuario."""
    if not sub_results:
        return ""
    joined = "\n\n".join(sub_results)
    if requires_sources(roles) and not extract_sources(joined):
        return "\n\n" + missing_sources_message()
    write_note = ""
    if "Archivo creado:" in joined or "Copia editada:" in joined:
        write_note = (
            "\n\nIMPORTANTE PARA LA RESPUESTA FINAL: hay herramientas que sí accedieron o "
            "escribieron archivos locales. Incluye las rutas exactas y no afirmes que no "
            "tienes acceso al filesystem local."
        )
    return "\n\nAquí tienes la información recopilada por tu equipo:\n" + joined + write_note


class DirectorRouter:
    """Encapsula la clasificación de roles del Director."""

    def classify(self, provider: Any, model: str, user_text: str) -> list[str]:
        stream = provider.stream_chat(
            model,
            [{"role": "user", "content": build_classifier_prompt(user_text)}],
        )
        return parse_roles("".join(list(stream)).lower())


class DirectorRoleExecutor:
    """Ejecuta roles en paralelo y preserva el orden estable de síntesis."""

    def __init__(
        self,
        max_workers: int = 4,
        todo_store: TodoStore | None = None,
        session_id: str | None = None,
    ):
        self.max_workers = max(1, max_workers)
        self.todo_store = todo_store
        self.session_id = session_id
        self._todo_lock = Lock()

    def run_roles(
        self,
        provider: Any,
        model: str,
        roles: list[RoleDefinition],
        query: str,
    ) -> list[str]:
        if not roles:
            return []

        self._set_role_plan(roles)
        results_by_index: dict[int, str] = {}
        worker_count = min(self.max_workers, len(roles))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(self._run_role, provider, model, role, query): (index, role)
                for index, role in enumerate(roles)
            }
            for future in as_completed(futures):
                index, role = futures[future]
                try:
                    role_result = future.result()
                except Exception as exc:
                    self._update_role_status(role.key, "blocked")
                    role_result = f"Error en el especialista {role.label}: {exc}"
                results_by_index[index] = f"{role.result_header}:\n{role_result}"

        return [results_by_index[index] for index in range(len(roles))]

    def _run_role(self, provider: Any, model: str, role: RoleDefinition, query: str) -> str:
        self._update_role_status(role.key, "running")
        write_instruction = (
            "Eres el único especialista autorizado para crear o editar archivos en exports. "
            "Si creas archivos, reporta cada ruta exacta devuelta por la tool."
            if role.key == "productor"
            else "No crees ni edites archivos; prepara análisis, estructura o requisitos para el productor."
        )
        sys_prompt = (
            f"Eres un {role.label}. Usa tus herramientas para resolver la consulta. "
            f"{write_instruction} "
            "Sé directo, solo entrega los datos encontrados sin saludos."
        )
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": query},
        ]
        stream = provider.stream_chat(model, messages, tools=role.tools)
        result = "".join(list(stream))
        self._update_role_status(role.key, "done")
        return result

    def _set_role_plan(self, roles: list[RoleDefinition]) -> None:
        if self.todo_store is None or self.session_id is None:
            return
        tasks = [(role.key, f"Ejecutar especialista {role.label}") for role in roles]
        with self._todo_lock:
            self.todo_store.set_plan(self.session_id, tasks)

    def _update_role_status(self, role_key: str, status: str) -> None:
        if self.todo_store is None or self.session_id is None:
            return
        with self._todo_lock:
            self.todo_store.update_status(self.session_id, role_key, status)
