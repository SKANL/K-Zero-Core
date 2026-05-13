"""Helpers internos para ejecutar tool calls solicitadas por providers."""
from collections.abc import Callable
import logging
from typing import Any

from k_zero_core.core.deliverable_intents import deliverable_intent_key
from k_zero_core.core.tool_output import prepare_tool_result
from k_zero_core.core.tools.registry import ToolPermission, ToolSpec, build_tool_specs


ToolCallable = Callable[..., Any] | ToolSpec
logger = logging.getLogger(__name__)
SENSITIVE_ARGUMENT_KEYS = ("api_key", "authorization", "password", "secret", "token", "url")


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


def _normalize_tool_specs(tools: list[ToolCallable]) -> list[ToolSpec]:
    """Convierte callables y ToolSpec al mismo contrato interno."""
    specs = [tool for tool in tools if isinstance(tool, ToolSpec)]
    callables = [tool for tool in tools if not isinstance(tool, ToolSpec)]
    return [*specs, *build_tool_specs(callables)]


def find_tool_by_name(tools: list[ToolCallable], name: str) -> ToolSpec | None:
    """Busca una tool por nombre y retorna su metadata."""
    return next((tool for tool in _normalize_tool_specs(tools) if tool.name == name), None)


def _redact_arguments(value: Any) -> Any:
    """Oculta valores sensibles antes de escribir argumentos en logs."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key).casefold()
            if any(sensitive in key_text for sensitive in SENSITIVE_ARGUMENT_KEYS):
                redacted[key] = "<redacted>"
            else:
                redacted[key] = _redact_arguments(item)
        return redacted
    if isinstance(value, list):
        return [_redact_arguments(item) for item in value]
    return value


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

    seen_write_intents: set[tuple[str, str]] = set()

    for tool_call in tool_calls:
        function_call = tool_call["function"]
        function_name = function_call["name"]
        arguments = function_call["arguments"]
        spec = find_tool_by_name(tools, function_name)
        if not spec:
            continue

        logger.info("Ejecutando tool: %s", function_name)
        logger.debug("Argumentos de tool %s: %s", function_name, _redact_arguments(arguments))
        intent_key = deliverable_intent_key(function_name, arguments)
        if intent_key is not None and intent_key in seen_write_intents:
            result = (
                f"Escritura duplicada bloqueada: ya existe una intención para "
                f"{intent_key[0]} '{intent_key[1]}' en este turno."
            )
        elif spec.permission == ToolPermission.DENY:
            result = f"Herramienta bloqueada por política: {function_name}"
        elif spec.permission == ToolPermission.ASK:
            result = (
                f"La herramienta '{function_name}' requiere confirmación explícita "
                "antes de ejecutarse. En este flujo aún no hay confirmación interactiva."
            )
        else:
            try:
                validated_arguments = spec.validate_arguments(arguments)
                result = spec.func(**validated_arguments)
                if intent_key is not None:
                    seen_write_intents.add(intent_key)
            except Exception as exc:
                validation_error = spec.validation_error(arguments)
                if validation_error:
                    result = f"Argumentos inválidos para '{function_name}': {validation_error}"
                else:
                    result = f"Error ejecutando herramienta: {exc}"

        messages.append(
            {
                "role": "tool",
                "content": prepare_tool_result(result, max_inline_chars=spec.max_inline_chars),
                "name": function_name,
                **({"tool_call_id": tool_call["id"]} if tool_call.get("id") else {}),
            }
        )

    return True
