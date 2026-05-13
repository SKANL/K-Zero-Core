"""
Interfaz base para todos los proveedores de IA.

Para agregar un nuevo proveedor:
  1. Crea una clase que herede de AIProvider en services/providers/
  2. Define el atributo de clase `key` con un identificador único (ej. "groq")
  3. Regístralo en services/providers/__init__.py

No necesitas modificar ningún otro archivo del proyecto.
"""
from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Any


class AIProvider(ABC):
    """Contrato que todo proveedor de IA debe cumplir."""

    key: str = ""  # Identificador único del proveedor — override en cada subclase
    cost: str = "free"
    privacy: str = "local"
    supports_tools: bool = False
    supports_streaming: bool = True
    is_local: bool = False

    @abstractmethod
    def get_display_name(self) -> str:
        """Nombre visible en los menús (ej. 'Ollama (Local)')."""

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """
        Retorna la lista de modelos disponibles en este proveedor.

        Raises:
            OllamaConnectionError o equivalente si el servicio no está disponible.
        """

    @abstractmethod
    def stream_chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list | None = None,
    ) -> Generator[str, None, None]:
        """
        Envía mensajes al proveedor y hace yield de los chunks de texto.

        Args:
            model: Identificador del modelo.
            messages: Historial en formato OpenAI-compatible.
            tools: Funciones callable opcionales para el agente.

        Yields:
            Fragmentos de texto de la respuesta.
        """
