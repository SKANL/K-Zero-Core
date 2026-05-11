"""Motor reusable de orquestación multi-agente para Director y workflows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from k_zero_core.modes.director_helpers import (
    DirectorRoleExecutor,
    DirectorRouter,
    ROLE_DEFINITIONS,
    RoleDefinition,
    build_director_context,
)
from k_zero_core.storage.memory_manager import TodoStore


@dataclass(frozen=True)
class DirectorResult:
    """Resultado de recopilación multi-agente listo para síntesis."""

    roles: list[str]
    sub_results: list[str]
    context: str


class DirectorEngine:
    """Coordina clasificación opcional, ejecución de roles y contexto final."""

    def __init__(
        self,
        *,
        router: DirectorRouter | None = None,
        max_workers: int = 4,
        todo_store: TodoStore | None = None,
        session_id: str | None = None,
    ) -> None:
        self.router = router or DirectorRouter()
        self.max_workers = max_workers
        self.todo_store = todo_store
        self.session_id = session_id

    def collect(
        self,
        provider: Any,
        model: str,
        query: str,
        *,
        roles: list[RoleDefinition] | None = None,
        role_keys: list[str] | tuple[str, ...] | None = None,
        classify: bool = True,
    ) -> DirectorResult:
        """Ejecuta roles explícitos o clasificados y devuelve contexto privado."""
        selected_roles = self._resolve_roles(provider, model, query, roles, role_keys, classify)
        executor = DirectorRoleExecutor(
            max_workers=self.max_workers,
            todo_store=self.todo_store,
            session_id=self.session_id,
        )
        sub_results = executor.run_roles(provider, model, selected_roles, query)
        role_names = [role.key for role in selected_roles]
        context = build_director_context(sub_results, roles=role_names)
        return DirectorResult(role_names, sub_results, context)

    def _resolve_roles(
        self,
        provider: Any,
        model: str,
        query: str,
        roles: list[RoleDefinition] | None,
        role_keys: list[str] | tuple[str, ...] | None,
        classify: bool,
    ) -> list[RoleDefinition]:
        if roles is not None:
            return list(roles)
        if role_keys is not None:
            return [ROLE_DEFINITIONS[key] for key in role_keys if key in ROLE_DEFINITIONS]
        if not classify:
            return []
        classified = self.router.classify(provider, model, query)
        return [ROLE_DEFINITIONS[key] for key in classified]
