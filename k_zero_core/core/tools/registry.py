"""Metadata interna para tools sin romper el contrato de get_all_tools()."""
from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolSpec:
    """Describe una tool registrada en K-Zero."""

    name: str
    func: Callable
    description: str = ""
    requires_env: tuple[str, ...] = field(default_factory=tuple)

    @property
    def available(self) -> bool:
        return all(os.getenv(var) for var in self.requires_env)


def build_tool_specs(tools: list[Callable]) -> list[ToolSpec]:
    """Construye metadata en el mismo orden que la lista pública de callables."""
    specs: list[ToolSpec] = []
    for tool in tools:
        requires_env: tuple[str, ...] = ()
        if tool.__name__ == "buscar_tavily":
            requires_env = ("TAVILY_API_KEY",)
        specs.append(
            ToolSpec(
                name=tool.__name__,
                func=tool,
                description=(tool.__doc__ or "").strip().splitlines()[0] if tool.__doc__ else "",
                requires_env=requires_env,
            )
        )
    return specs
