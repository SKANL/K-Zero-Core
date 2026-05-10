"""Tool de tareas ligeras por sesión."""
from __future__ import annotations

from k_zero_core.storage.memory_manager import TodoStore


def todo(session_id: str = "default", action: str = "read", todos: list[dict] | None = None) -> str:
    """
    Lee o propone tareas de sesión. Las escrituras quedan restringidas al flujo interno.
    """
    store = TodoStore()
    normalized_action = action.strip().lower()
    if normalized_action == "read":
        items = store.read(session_id)
        if not items:
            return "No hay tareas activas."
        return "\n".join(f"- [{item['status']}] {item['id']}: {item['content']}" for item in items)
    if normalized_action == "write":
        return "La escritura de tareas requiere confirmación explícita; no se ejecutó ningún cambio."
    return "Acción inválida. Usa action='read'."
