"""Reflexión conservadora de memoria con confirmación del usuario."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from k_zero_core.services.chat_session import ChatSession
from k_zero_core.storage.memory_manager import MemoryStore, StoreResult


CONFIRMATION_PHRASES = {
    "si guardalo",
    "sí guardalo",
    "si, guardalo",
    "sí, guardalo",
    "si guárdalo",
    "sí guárdalo",
    "si, guárdalo",
    "sí, guárdalo",
    "guardalo",
    "guárdalo",
}

_REMEMBER_PATTERNS = [
    re.compile(r"^\s*recuerda\s+que\s+(?P<content>.+)$", re.IGNORECASE),
    re.compile(r"^\s*ten\s+en\s+cuenta\s+que\s+(?P<content>.+)$", re.IGNORECASE),
    re.compile(r"^\s*no\s+olvides\s+que\s+(?P<content>.+)$", re.IGNORECASE),
]
_SECRET_HINTS = re.compile(
    r"\b(api[_ -]?key|token|password|contraseña|secreto|secret|credential|credencial)\b",
    re.IGNORECASE,
)


class MemoryDecision(BaseModel):
    """Decisión validada antes de proponer escritura persistente."""

    should_remember: bool
    target: Literal["memory", "user"] = "memory"
    content: str = Field(default="", min_length=1, max_length=500)


@dataclass(frozen=True)
class PendingMemory:
    target: Literal["memory", "user"]
    content: str


def _sentence_case(text: str) -> str:
    stripped = text.strip().strip('"').strip("'").strip()
    if not stripped:
        return stripped
    if not stripped.endswith("."):
        stripped += "."
    return stripped[0].upper() + stripped[1:]


class MemoryReflectionService:
    """Detecta candidatos de memoria y exige confirmación antes de escribir."""

    def __init__(self, store: MemoryStore | None = None):
        self.store = store or MemoryStore()

    def confirm_if_requested(self, chat_session: ChatSession, user_text: str) -> StoreResult | None:
        """Persiste memoria pendiente solo cuando el usuario confirma explícitamente."""
        pending = self._pending_from_session(chat_session)
        if pending is None:
            return None
        if user_text.strip().lower().replace(".", "").replace("!", "") not in CONFIRMATION_PHRASES:
            return None

        result = self.store.add(pending.target, pending.content)
        chat_session.metadata.pop("pending_memory", None)
        return result

    def consider_user_message(self, chat_session: ChatSession, user_text: str) -> str | None:
        """Propone guardar memoria cuando el texto del usuario lo pide claramente."""
        if chat_session.metadata.get("pending_memory"):
            return None

        decision = self._decide(user_text)
        if not decision.should_remember:
            return None

        result = self.store.validate_entry(decision.target, decision.content)
        if not result.ok:
            return None
        chat_session.metadata["pending_memory"] = {
            "target": decision.target,
            "content": decision.content,
        }
        return (
            f"Puedo guardar esto en memoria: {decision.content} "
            "Responde 'sí, guárdalo' para confirmar."
        )

    def _decide(self, user_text: str) -> MemoryDecision:
        content = self._extract_explicit_memory(user_text)
        if not content or _SECRET_HINTS.search(content):
            return MemoryDecision.model_validate({"should_remember": False, "content": "ignorado"})

        target: Literal["memory", "user"] = "memory"
        lowered = content.lower()
        if lowered.startswith(("prefiero ", "me gusta ", "mi ")):
            target = "user"
        try:
            return MemoryDecision.model_validate(
                {
                    "should_remember": True,
                    "target": target,
                    "content": _sentence_case(content),
                }
            )
        except ValidationError:
            return MemoryDecision.model_validate({"should_remember": False, "content": "ignorado"})

    def _extract_explicit_memory(self, user_text: str) -> str | None:
        for pattern in _REMEMBER_PATTERNS:
            match = pattern.match(user_text)
            if match:
                return match.group("content").strip()
        return None

    def _pending_from_session(self, chat_session: ChatSession) -> PendingMemory | None:
        pending = chat_session.metadata.get("pending_memory")
        if not isinstance(pending, dict):
            return None
        try:
            decision = MemoryDecision.model_validate(
                {
                    "should_remember": True,
                    "target": pending.get("target", "memory"),
                    "content": pending.get("content", ""),
                }
            )
        except ValidationError:
            chat_session.metadata.pop("pending_memory", None)
            return None
        return PendingMemory(decision.target, decision.content)
