"""Persistencia de workflows declarativos del usuario."""
from __future__ import annotations

import json
import shutil
from dataclasses import fields, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from k_zero_core.core.config import WORKFLOWS_DIR
from k_zero_core.core.tools.toolsets import TOOLSETS
from k_zero_core.modes import MODE_REGISTRY
from k_zero_core.modes.director_helpers import ROLE_DEFINITIONS
from k_zero_core.workflows.models import (
    WorkflowAudience,
    WorkflowCost,
    WorkflowDefinition,
    WorkflowInput,
    WorkflowOutput,
    WorkflowPrivacy,
)


def _safe_key(key: str) -> str:
    return "".join(char for char in key if char.isalnum() or char in ("-", "_")) or "workflow"


def _enum_value(enum_cls, value: Any, field_name: str):
    try:
        return enum_cls(value)
    except ValueError as exc:
        raise ValueError(f"Workflow inválido: valor desconocido para '{field_name}': {value}") from exc


def _json_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    return value


class WorkflowStore:
    """CRUD mínimo para workflows JSON sin ejecutar código del usuario."""

    def __init__(self, root: Path = WORKFLOWS_DIR) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        return self.root / f"{_safe_key(key)}.json"

    def list(self) -> list[WorkflowDefinition]:
        workflows: list[WorkflowDefinition] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                workflows.append(self._from_dict(json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return workflows

    def load(self, key: str) -> WorkflowDefinition:
        path = self._path_for(key)
        if not path.exists():
            raise FileNotFoundError(path)
        return self._from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        self._validate(workflow)
        self._path_for(workflow.key).write_text(
            json.dumps(self._to_dict(workflow), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return workflow

    def save_raw(self, data: dict[str, Any]) -> WorkflowDefinition:
        """Valida y guarda un workflow desde datos JSON ya parseados."""
        return self.save(self._from_dict(data))

    def create_from_template(self, key: str, template_key: str) -> WorkflowDefinition:
        from k_zero_core.workflows.registry import get_workflow

        template = get_workflow(template_key)
        workflow = replace(
            template,
            key=_safe_key(key),
            name=key.replace("_", " ").strip().title() or template.name,
        )
        return self.save(workflow)

    def import_workflow(self, path: Path) -> WorkflowDefinition:
        resolved = path.expanduser().resolve()
        try:
            resolved.relative_to(self.root.resolve())
        except ValueError as exc:
            raise ValueError("Solo se importan workflows desde el directorio configurado de workflows.") from exc
        data = json.loads(resolved.read_text(encoding="utf-8"))
        return self.save_raw(data)

    def export_workflow(self, key: str, destination: Path) -> Path:
        source = self._path_for(key)
        if not source.exists():
            raise FileNotFoundError(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        return destination

    def _from_dict(self, data: dict[str, Any]) -> WorkflowDefinition:
        if not isinstance(data, dict):
            raise ValueError("Workflow inválido: el JSON debe ser un objeto.")
        key = str(data.get("key", "")).strip()
        if not key:
            raise ValueError("Workflow inválido: falta el campo obligatorio 'key'.")
        return WorkflowDefinition(
            key=_safe_key(key),
            name=str(data.get("name") or key),
            description=str(data.get("description") or ""),
            audience=_enum_value(WorkflowAudience, data.get("audience", WorkflowAudience.USER.value), "audience"),
            cost=_enum_value(WorkflowCost, data.get("cost", WorkflowCost.FREE.value), "cost"),
            privacy=_enum_value(WorkflowPrivacy, data.get("privacy", WorkflowPrivacy.LOCAL.value), "privacy"),
            input_type=_enum_value(WorkflowInput, data.get("input_type", WorkflowInput.TEXT.value), "input_type"),
            output_type=_enum_value(WorkflowOutput, data.get("output_type", WorkflowOutput.TEXT.value), "output_type"),
            mode_key=str(data.get("mode_key", "")),
            default_provider=str(data.get("default_provider", "ollama")),
            toolsets=tuple(str(item) for item in data.get("toolsets", [])),
            roles=tuple(str(item) for item in data.get("roles", [])),
            system_prompt=str(data.get("system_prompt", "")),
            requires_llm=bool(data.get("requires_llm", True)),
            requires_confirmation_for_writes=bool(data.get("requires_confirmation_for_writes", True)),
            writes_files=bool(data.get("writes_files", False)),
            write_description=str(data.get("write_description", "escribe archivos locales")),
        )

    def _validate(self, workflow: WorkflowDefinition) -> None:
        if workflow.mode_key and workflow.mode_key not in MODE_REGISTRY:
            raise ValueError(f"Workflow inválido: modo desconocido '{workflow.mode_key}'.")
        for values, registry, label in (
            (workflow.toolsets, TOOLSETS, "toolset"),
            (workflow.roles, ROLE_DEFINITIONS, "rol"),
        ):
            unknown = [name for name in values if name not in registry]
            if unknown:
                raise ValueError(f"Workflow inválido: {label} desconocido: " + ", ".join(unknown))

    def _to_dict(self, workflow: WorkflowDefinition) -> dict[str, Any]:
        return {field.name: _json_value(getattr(workflow, field.name)) for field in fields(workflow)}
