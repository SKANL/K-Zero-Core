"""Registro de workflows built-in y declarativos."""
from __future__ import annotations

from contextlib import suppress

from k_zero_core.workflows.definitions import BUILTIN_WORKFLOWS
from k_zero_core.workflows.models import WorkflowDefinition


def list_workflows(*, include_user: bool = True) -> list[WorkflowDefinition]:
    """Lista workflows built-in y, si existen, workflows declarativos del usuario."""
    workflows = list(BUILTIN_WORKFLOWS)
    if include_user:
        with suppress(Exception):
            from k_zero_core.storage.workflow_manager import WorkflowStore

            workflows.extend(WorkflowStore().list())
    return workflows


def get_workflow(key: str) -> WorkflowDefinition:
    """Obtiene un workflow por clave."""
    for workflow in list_workflows():
        if workflow.key == key:
            return workflow
    raise KeyError(f"Workflow no encontrado: {key}")
