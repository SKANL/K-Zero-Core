"""Ejecución y validación de workflows guiados."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from k_zero_core.core.tools.toolsets import resolve_toolset_specs
from k_zero_core.modes import MODE_REGISTRY
from k_zero_core.modes.mode_streaming import save_and_output_response, stream_text_response
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.services.director_engine import DirectorEngine
from k_zero_core.workflows.models import WorkflowDefinition, WorkflowPrivacy


class WorkflowProviderError(RuntimeError):
    """El provider elegido no cumple las capacidades requeridas por el workflow."""


@dataclass(frozen=True)
class WorkflowRunSummary:
    cost: str
    privacy: str
    requires_network: bool
    writes_files: bool
    message: str


class WorkflowPluginAdapter:
    """Adapta un WorkflowDefinition al contrato mínimo esperado por la CLI."""

    def __init__(self, workflow: WorkflowDefinition) -> None:
        self.workflow = workflow

    @property
    def requires_llm(self) -> bool:
        return self.workflow.requires_llm

    @property
    def force_input_type(self) -> str | None:
        return self.workflow.input_type.value

    def get_name(self) -> str:
        return self.workflow.name

    def get_description(self) -> str:
        return self.workflow.description

    def get_default_system_prompt(self) -> str:
        return self.workflow.system_prompt

    def get_voice(self) -> str:
        return "es-MX-DaliaNeural"


class WorkflowEngine:
    """Valida, resume y ejecuta workflows con dependencias inyectables."""

    def __init__(
        self,
        *,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
        director_engine_cls: type[DirectorEngine] = DirectorEngine,
    ) -> None:
        self.input_func = input_func
        self.output_func = output_func
        self.director_engine_cls = director_engine_cls

    def summarize(self, workflow: WorkflowDefinition) -> WorkflowRunSummary:
        specs = []
        for toolset in workflow.toolsets:
            specs.extend(resolve_toolset_specs(toolset))
        requires_network = workflow.privacy != WorkflowPrivacy.LOCAL or any(spec.requires_network for spec in specs)
        writes_files = workflow.writes_files or any(spec.writes_files for spec in specs)
        privacy = WorkflowPrivacy.NETWORK.value if requires_network else workflow.privacy.value
        write_text = workflow.write_description if workflow.writes_files else "escribe copias en exports"
        if not writes_files:
            write_text = "no escribe archivos"
        network_text = "usa red/internet" if requires_network else "100% local"
        cost_text = "gratis por defecto" if workflow.cost.value == "free" else workflow.cost.value
        message = f"{workflow.name}: {cost_text}, privacidad={privacy}, {network_text}, {write_text}."
        return WorkflowRunSummary(workflow.cost.value, privacy, requires_network, writes_files, message)

    def confirm_if_needed(self, workflow: WorkflowDefinition, summary: WorkflowRunSummary) -> bool:
        """Solicita confirmación explícita antes de workflows que escriben archivos."""
        if not summary.writes_files or not workflow.requires_confirmation_for_writes:
            return True
        answer = self.input_func(
            f"Este workflow puede escribir archivos locales ({summary.message}). "
            "Escribe 'sí' para confirmar: "
        )
        normalized = answer.strip().lower()
        return normalized in {"si", "sí", "s", "yes", "y"}

    def validate_provider(self, workflow: WorkflowDefinition, provider: Any) -> None:
        if workflow.requires_tools and provider is not None and not getattr(provider, "supports_tools", False):
            raise WorkflowProviderError(
                f"El provider '{provider.get_display_name()}' no soporta tools requeridas por '{workflow.name}'."
            )

    def run(
        self,
        workflow: WorkflowDefinition,
        *,
        chat_session: ChatSession | None = None,
        io_handler: Any | None = None,
        provider: Any | None = None,
        summary: WorkflowRunSummary | None = None,
        show_summary: bool = True,
    ) -> None:
        """Ejecuta un workflow built-in sobre modo existente o DirectorEngine."""
        summary = summary or self.summarize(workflow)
        if show_summary:
            self.output_func(summary.message)
        if provider is not None:
            self.validate_provider(workflow, provider)
        if not self.confirm_if_needed(workflow, summary):
            self.output_func("Workflow cancelado: no se confirmó la escritura local.")
            return

        if workflow.mode_key:
            mode_cls = MODE_REGISTRY[workflow.mode_key]
            mode = mode_cls()
            if chat_session is None:
                chat_session = ChatSession(provider=provider)
            mode.run(chat_session, io_handler)
            return

        if chat_session is None or chat_session.provider is None:
            raise WorkflowProviderError(f"El workflow '{workflow.name}' requiere una sesión con provider.")
        query = self.input_func("Describe la tarea o resultado que necesitas: ").strip()
        if not query:
            self.output_func("No se recibió una tarea para ejecutar.")
            return

        director = self.director_engine_cls(session_id=chat_session.session_id)
        result = director.collect(
            chat_session.provider,
            chat_session.model,
            query,
            role_keys=workflow.roles,
            classify=False,
        )
        if "FUENTES REQUERIDAS:" in result.context:
            message = result.context.strip()
            chat_session.add_user_message(query)
            chat_session.add_assistant_message(message)
            self.output_func(message)
            if io_handler is not None:
                io_handler.output_response(message)
            return

        chat_session.add_user_message(query + result.context)
        stream = chat_session.provider.stream_chat(chat_session.model, chat_session.messages)
        response = stream_text_response(stream, workflow.name)
        save_and_output_response(chat_session, io_handler, response)
        chat_session.messages[-2] = {"role": "user", "content": query}
