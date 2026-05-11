"""Modelos declarativos para workflows guiados."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class WorkflowAudience(StrEnum):
    USER = "user"
    TECHNICAL = "technical"


class WorkflowCost(StrEnum):
    FREE = "free"
    OPTIONAL_PAID = "optional_paid"
    PAID = "paid"


class WorkflowPrivacy(StrEnum):
    LOCAL = "local"
    NETWORK = "network"
    CLOUD = "cloud"


class WorkflowInput(StrEnum):
    TEXT = "text"
    AUDIO = "audio"


class WorkflowOutput(StrEnum):
    TEXT = "text"
    AUDIO = "audio"


@dataclass(frozen=True)
class WorkflowDefinition:
    """Define una tarea guiada o workflow técnico reutilizable."""

    key: str
    name: str
    description: str
    audience: WorkflowAudience = WorkflowAudience.USER
    cost: WorkflowCost = WorkflowCost.FREE
    privacy: WorkflowPrivacy = WorkflowPrivacy.LOCAL
    input_type: WorkflowInput = WorkflowInput.TEXT
    output_type: WorkflowOutput = WorkflowOutput.TEXT
    mode_key: str = ""
    default_provider: str = "ollama"
    toolsets: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    system_prompt: str = ""
    requires_llm: bool = True
    requires_confirmation_for_writes: bool = True
    writes_files: bool = False
    write_description: str = "escribe archivos locales"

    @property
    def requires_tools(self) -> bool:
        return bool(self.toolsets or self.roles)
