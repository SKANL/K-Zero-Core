from typing import List, Dict, Any, Optional, Generator

import ollama

from k_zero_core.core.exceptions import OllamaConnectionError
from k_zero_core.core.tool_executor import execute_tool_calls
from k_zero_core.services.providers.base_provider import AIProvider


class OllamaProvider(AIProvider):
    """Proveedor de IA usando Ollama ejecutándose en local."""

    key = "ollama"

    def get_display_name(self) -> str:
        return "Ollama (Local)"

    from functools import lru_cache

    @lru_cache(maxsize=1)
    def get_available_models(self) -> List[str]:
        """Retorna los modelos instalados localmente en Ollama."""
        try:
            response = ollama.list()
            return [m['model'] for m in response.get('models', [])]
        except Exception as e:
            raise OllamaConnectionError(
                f"No se pudo conectar a Ollama. Asegúrate de que la app esté corriendo. Detalle: {e}"
            )

    def _handle_tool_calls(
        self,
        response_message: Dict[str, Any],
        messages: List[Dict[str, Any]],
        tools: List
    ) -> bool:
        """
        Ejecuta las herramientas solicitadas por el modelo y actualiza el historial.
        Retorna True si se ejecutaron herramientas, False en caso contrario.
        """
        return execute_tool_calls(response_message, messages, tools)

    def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List] = None,
    ) -> Generator[str, None, None]:
        """
        Envía mensajes a Ollama y hace yield de los chunks de la respuesta.
        Si el modelo decide usar herramientas, las ejecuta y continúa el streaming.
        """
        try:
            if tools:
                response = ollama.chat(
                    model=model, messages=messages, tools=tools, stream=False
                )
                
                response_message = response.get('message', {})
                if self._handle_tool_calls(response_message, messages, tools):
                    # Retomar streaming con los resultados de las herramientas en el historial
                    stream = ollama.chat(model=model, messages=messages, stream=True)
                    for chunk in stream:
                        yield chunk['message']['content']
                    return

            stream = ollama.chat(model=model, messages=messages, stream=True)
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']

        except OllamaConnectionError:
            raise
        except Exception as e:
            raise OllamaConnectionError(f"Error durante la generación: {e}")
