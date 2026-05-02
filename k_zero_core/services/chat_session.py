import uuid
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from k_zero_core.services.providers.base_provider import AIProvider


class ChatSession:
    """Manages the state and history of a single chat conversation."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        model: str = "",
        provider: Optional["AIProvider"] = None,
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.model = model
        self.provider = provider
        self.messages: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}  # estado arbitrario por modo (ej. RAG collection_id)

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
