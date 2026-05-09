"""Configuración de sesiones de chat para la CLI."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from k_zero_core.cli.menus import choose_model, choose_system_prompt
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.services.prompt_composer import compose_system_prompt
from k_zero_core.services.providers import get_provider
from k_zero_core.storage.session_manager import load_session


def setup_chat_session(
    plugin: Any,
    provider: Any,
    session_id: Optional[str],
    *,
    choose_model_func: Callable[[Any], str] = choose_model,
    choose_system_prompt_func: Callable[[str], str] = choose_system_prompt,
    compose_prompt_func: Callable[[str], str] = compose_system_prompt,
    load_session_func: Callable[[str], dict[str, Any]] = load_session,
    get_provider_func: Callable[[str], Any] = get_provider,
) -> ChatSession:
    """Configura y retorna una sesión cargada o nueva para un modo CLI."""
    chat = ChatSession(session_id=session_id, provider=provider)

    if session_id:
        session_data = load_session_func(session_id)
        saved_provider_key = session_data.get("provider", "ollama")

        if saved_provider_key != provider.key:
            chat.provider = get_provider_func(saved_provider_key)
            print(f"(Restaurando proveedor '{saved_provider_key}' de la sesión guardada)")

        chat.model = session_data.get("model", "")
        chat.metadata = session_data.get("metadata", {})
        chat.load_history(session_data.get("messages", []))
        print(f"\nRetomando sesión con {chat.model} ({chat.provider.get_display_name()}) en modo {plugin.get_name()}...")
        return chat

    chat.model = choose_model_func(provider)

    print("\n(Opcional) Puedes elegir un System Prompt guardado, o usar el que viene por defecto para este Modo.")
    default_prompt = plugin.get_default_system_prompt()
    sys_prompt = choose_system_prompt_func(default_prompt or "")

    if sys_prompt:
        chat.set_system_prompt(compose_prompt_func(sys_prompt))
        print("System prompt personalizado cargado.")
    elif default_prompt:
        chat.set_system_prompt(compose_prompt_func(default_prompt))
        print("System prompt por defecto del modo cargado.")

    print(f"\n--- Iniciando nuevo chat con {chat.model} ({chat.provider.get_display_name()}) ---")
    return chat
