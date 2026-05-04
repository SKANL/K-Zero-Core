import secrets
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from k_zero_core.services.providers.base_provider import AIProvider


@dataclass
class ChatSession:
    """Manages the state and history of a single chat conversation."""

    session_id: Optional[str] = None
    model: str = ""
    provider: Optional["AIProvider"] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)  # estado arbitrario por modo (ej. RAG collection_id)

    def __post_init__(self):
        if not self.session_id:
            self.session_id = secrets.token_hex(8)

    @property
    def provider_key(self) -> str:
        """Clave estable del proveedor activo para persistencia."""
        return self.provider.key if self.provider else "ollama"

    def set_system_prompt(self, prompt: str) -> None:
        """Sets or replaces the system prompt."""
        self.messages = [m for m in self.messages if m.get('role') != 'system']
        if prompt.strip():
            self.messages.insert(0, {'role': 'system', 'content': prompt.strip()})

    def add_user_message(self, content: str) -> None:
        """Appends a user message to the history."""
        self.messages.append({'role': 'user', 'content': content})

    def add_assistant_message(self, content: str) -> None:
        """Appends an assistant message to the history."""
        self.messages.append({'role': 'assistant', 'content': content})

    def load_history(self, messages: List[Dict[str, Any]]) -> None:
        """Loads an existing message history."""
        self.messages = messages
