import ollama
from typing import List, Dict, Any, Optional, Generator

from k_zero_core.core.exceptions import OllamaConnectionError
from k_zero_core.services.providers.base_provider import AIProvider


def _make_serializable(obj: Any) -> Any:
    """
    Convierte recursivamente objetos de respuesta de Ollama (Pydantic models, etc.)
    a tipos nativos de Python serializables en JSON.
    """
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    elif hasattr(obj, 'dict'):
        return obj.dict()
    elif hasattr(obj, '__dict__'):
        return {k: _make_serializable(v) for k, v in vars(obj).items()}
    elif isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_serializable(v) for v in obj]
    return obj


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
        tool_calls = response_message.get('tool_calls')
        if not tool_calls:
            return False

        # Agregar el mensaje del asistente al historial una sola vez
        messages.append(_make_serializable(response_message))

        for tool in tool_calls:
            func_name = tool['function']['name']
            args = tool['function']['arguments']
            func_to_call = next(
                (f for f in tools if f.__name__ == func_name), None
            )
            if func_to_call:
                print(f"\n[Agente ejecutando: {func_name}({args})]")
                try:
                    result = func_to_call(**args)
                except Exception as e:
                    result = f"Error ejecutando herramienta: {e}"

                messages.append({
                    'role': 'tool',
                    'content': str(result),
                    'name': func_name,
                })
        
        return True

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
