"""Memoria curada y tareas ligeras persistentes."""
from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from k_zero_core.core.config import DATA_DIR

ENTRY_DELIMITER = "\n§\n"
DEFAULT_MEMORY_DIR = DATA_DIR / "memory"

_INJECTION_PATTERNS = [
    re.compile(r"ignora\s+(todas\s+)?(tus\s+)?instrucciones", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?(previous\s+)?instructions", re.IGNORECASE),
    re.compile(r"act[uú]a\s+como\s+si\s+no\s+tuvieras\s+restricciones", re.IGNORECASE),
]
VALID_TODO_STATUSES = {"pending", "running", "done", "blocked"}


@dataclass(frozen=True)
class StoreResult:
    ok: bool
    message: str


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def _safe_session_id(session_id: str) -> str:
    return "".join(c for c in session_id if c.isalnum() or c in ("-", "_")) or "default"


def _scan_content(content: str) -> str | None:
    for char in content:
        if "\U000e0000" <= char <= "\U000e007f":
            return f"Contenido bloqueado: carácter invisible U+{ord(char):04X}."
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(content):
            return "Contenido bloqueado: parece una instrucción de bypass o prompt injection."
    return None


class MemoryStore:
    """Memoria acotada en MEMORY.md y USER.md."""

    def __init__(self, root: Path = DEFAULT_MEMORY_DIR, memory_char_limit: int = 2200, user_char_limit: int = 1375):
        self.root = root
        self.memory_char_limit = memory_char_limit
        self.user_char_limit = user_char_limit

    def _path_for(self, target: str) -> Path:
        if target == "user":
            return self.root / "USER.md"
        return self.root / "MEMORY.md"

    def _limit_for(self, target: str) -> int:
        return self.user_char_limit if target == "user" else self.memory_char_limit

    def read(self, target: str = "memory") -> list[str]:
        path = self._path_for(target)
        if not path.exists():
            return []
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        return [entry for entry in content.split(ENTRY_DELIMITER) if entry.strip()]

    def validate_entry(self, target: str, content: str) -> StoreResult:
        """Valida una entrada sin persistirla."""
        content = content.strip()
        if target not in ("memory", "user"):
            return StoreResult(False, "Target inválido. Usa 'memory' o 'user'.")
        if not content:
            return StoreResult(False, "La entrada de memoria está vacía.")
        scan_error = _scan_content(content)
        if scan_error:
            return StoreResult(False, scan_error)

        entries = self.read(target)
        rendered = ENTRY_DELIMITER.join(list(dict.fromkeys(entries + [content])))
        limit = self._limit_for(target)
        if len(rendered) > limit:
            return StoreResult(False, f"Memoria excedería el límite de {limit} caracteres.")
        return StoreResult(True, "Entrada de memoria válida.")

    def add(self, target: str, content: str) -> StoreResult:
        content = content.strip()
        validation = self.validate_entry(target, content)
        if not validation.ok:
            return validation

        entries = self.read(target)
        new_entries = list(dict.fromkeys(entries + [content]))
        rendered = ENTRY_DELIMITER.join(new_entries)
        limit = self._limit_for(target)
        if len(rendered) > limit:
            return StoreResult(False, f"Memoria excedería el límite de {limit} caracteres.")
        _atomic_write(self._path_for(target), rendered)
        return StoreResult(True, f"Memoria actualizada ({len(rendered)}/{limit} caracteres).")


class TodoStore:
    """Tareas por sesión guardadas en JSON."""

    def __init__(self, root: Path = DEFAULT_MEMORY_DIR / "todos"):
        self.root = root

    def _path_for(self, session_id: str) -> Path:
        return self.root / f"{_safe_session_id(session_id)}.json"

    def read(self, session_id: str) -> list[dict[str, str]]:
        path = self._path_for(session_id)
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def write(self, session_id: str, todos: list[dict[str, Any]]) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        for item in todos:
            status = str(item.get("status", "pending")).strip() or "pending"
            normalized.append(
                {
                    "id": str(item.get("id", "")).strip(),
                    "content": str(item.get("content", "")).strip(),
                    "status": status if status in VALID_TODO_STATUSES else "pending",
                }
            )
        normalized = [item for item in normalized if item["id"] and item["content"]]
        _atomic_write(self._path_for(session_id), json.dumps(normalized, indent=2, ensure_ascii=False))
        return normalized

    def set_plan(self, session_id: str, tasks: Iterable[tuple[str, str]]) -> list[dict[str, str]]:
        """Reemplaza el plan de trabajo de una sesión preservando el orden recibido."""
        return self.write(
            session_id,
            [{"id": task_id, "content": content, "status": "pending"} for task_id, content in tasks],
        )

    def update_status(self, session_id: str, task_id: str, status: str) -> list[dict[str, str]]:
        """Actualiza el estado de una tarea existente sin reordenar la lista."""
        normalized_status = status if status in VALID_TODO_STATUSES else "pending"
        items = self.read(session_id)
        updated: list[dict[str, str]] = []
        found = False
        for item in items:
            if item["id"] == task_id:
                updated.append({**item, "status": normalized_status})
                found = True
            else:
                updated.append(item)
        if not found:
            updated.append({"id": task_id, "content": task_id, "status": normalized_status})
        return self.write(session_id, updated)
