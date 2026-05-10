"""Tools de memoria curada."""
from __future__ import annotations

from k_zero_core.storage.memory_manager import MemoryStore


def memory(action: str = "read", target: str = "memory", content: str = "") -> str:
    """
    Lee memoria curada persistente. Las escrituras requieren confirmación fuera de este ciclo.
    """
    store = MemoryStore()
    normalized_action = action.strip().lower()
    if normalized_action == "read":
        entries = store.read(target)
        if not entries:
            return "No hay memoria guardada."
        return "\n".join(f"- {entry}" for entry in entries)
    if normalized_action in {"add", "replace", "remove", "write"}:
        return "La escritura de memoria requiere confirmación explícita; no se ejecutó ningún cambio."
    return "Acción inválida. Usa action='read'."
