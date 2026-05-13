from typing import List, Dict, Any, Optional, Generator

import ollama
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from k_zero_core.core.exceptions import OllamaConnectionError
from k_zero_core.core.tool_executor import execute_tool_calls
from k_zero_core.services.providers.base_provider import AIProvider


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.1, min=0.1, max=1),
    reraise=True,
)
def _retryable_ollama_call(func, *args, **kwargs):
    """Ejecuta una llamada a Ollama con backoff para cargas lentas del modelo local."""
    return func(*args, **kwargs)


class OllamaProvider(AIProvider):
    """Proveedor de IA usando Ollama ejecutándose en local."""

    key = "ollama"
    cost = "free"
    privacy = "local"
    supports_tools = True
    supports_streaming = True
    is_local = True

    def get_display_name(self) -> str:
        return "Ollama (Local)"

    from functools import lru_cache

    @lru_cache(maxsize=1)
    def get_available_models(self) -> List[str]:
        """Retorna los modelos instalados localmente en Ollama."""
        try:
            response = _retryable_ollama_call(ollama.list)
            return [m['model'] for m in response.get('models', [])]
        except Exception as e:
            raise OllamaConnectionError(
                f"No se pudo conectar a Ollama. Asegúrate de que la app esté corriendo. Detalle: {e}"
            )

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
                response = _retryable_ollama_call(
                    ollama.chat,
                    model=model, messages=messages, tools=tools, stream=False
                )
                
                response_message = response.get('message', {})
                if execute_tool_calls(response_message, messages, tools):
                    stream = _retryable_ollama_call(ollama.chat, model=model, messages=messages, stream=True)
                    for chunk in stream:
                        yield chunk['message']['content']
                    return

            stream = _retryable_ollama_call(ollama.chat, model=model, messages=messages, stream=True)
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']

        except OllamaConnectionError:
            raise
        except Exception as e:
            raise OllamaConnectionError(f"Error durante la generación: {e}")
