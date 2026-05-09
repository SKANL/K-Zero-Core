"""Helpers internos para ejecutar tool calls solicitadas por providers."""
from collections.abc import Callable
from typing import Any

from k_zero_core.core.tool_output import prepare_tool_result


ToolCallable = Callable[..., Any]


def make_serializable(obj: Any) -> Any:
    """
    Convierte recursivamente objetos de respuesta de providers a tipos JSON nativos.
    """
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return {key: make_serializable(value) for key, value in vars(obj).items()}
    if isinstance(obj, dict):
        return {key: make_serializable(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [make_serializable(value) for value in obj]
    return obj


def find_tool_by_name(tools: list[ToolCallable], name: str) -> ToolCallable | None:
    """Busca una tool callable por su atributo __name__."""
    return next((tool for tool in tools if getattr(tool, "__name__", "") == name), None)


def execute_tool_calls(
    response_message: dict[str, Any],
    messages: list[dict[str, Any]],
    tools: list[ToolCallable],
) -> bool:
    """
    Ejecuta las herramientas solicitadas por el modelo y actualiza el historial.

    Retorna True cuando el provider pidió tool calls, incluso si una tool concreta no
    se encontró, para preservar el flujo actual de segunda llamada al modelo.
    """
    tool_calls = response_message.get("tool_calls")
    if not tool_calls:
        return False

    messages.append(make_serializable(response_message))

    for tool_call in tool_calls:
        function_call = tool_call["function"]
        function_name = function_call["name"]
        arguments = function_call["arguments"]
        function_to_call = find_tool_by_name(tools, function_name)
        if not function_to_call:
            continue

        print(f"\n[Agente ejecutando: {function_name}({arguments})]")
        try:
            result = function_to_call(**arguments)
        except Exception as exc:
            result = f"Error ejecutando herramienta: {exc}"

        messages.append(
            {
                "role": "tool",
                "content": prepare_tool_result(result),
                "name": function_name,
            }
        )

    return True
