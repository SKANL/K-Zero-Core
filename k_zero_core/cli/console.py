import sys

from k_zero_core.modes import MODE_REGISTRY
from k_zero_core.cli.menus import (
    choose_provider,
    manage_sessions, choose_mode, choose_io_mode,
)
from k_zero_core.cli.io_setup import setup_io_handler
from k_zero_core.cli.session_setup import setup_chat_session
from k_zero_core.storage.session_manager import save_session
from k_zero_core.core.exceptions import APIVoiceException
from k_zero_core.core.plugin_loader import load_external_plugins


def run() -> None:
    """Main entry point for the CLI."""
    
    # 0. Cargar plugins dinámicos primero
    load_external_plugins()
    
    print("Bienvenido a Ollama CLI")

    chat = None
    plugin = None

    try:
        # 1. Elegir modo de interacción primero
        mode_key = choose_mode()
        plugin = MODE_REGISTRY[mode_key]()

        # 2. Elegir proveedor de IA (se omite si no requiere LLM)
        provider = choose_provider() if plugin.requires_llm else None

        # 3. Elegir estrategia de I/O
        if plugin.force_input_type:
            input_type = plugin.force_input_type
            output_type = "text" # por defecto en modos de solo entrada
            print(f"\n[Info] El modo '{plugin.get_name()}' forzará la entrada de {input_type}.")
        else:
            input_type, output_type = choose_io_mode()

        # 4. Gestionar sesiones
        if plugin.requires_llm:
            session_id = manage_sessions()
            chat = setup_chat_session(plugin, provider, session_id)
        else:
            chat = None
            print(f"\n--- Iniciando {plugin.get_name()} ---")

        # 5. Inicializar hardware de audio
        io_handler = setup_io_handler(input_type, output_type, plugin)

        # 6. Ejecutar el modo
        try:
            plugin.run(chat, io_handler)
        except KeyboardInterrupt:
            print(f"\nSaliendo del Modo {plugin.get_name()}...")

    except APIVoiceException as e:
        print(f"\nError de la aplicación: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nSaliendo...")
    except Exception as e:
        print(f"\nOcurrió un error inesperado: {e}")
        sys.exit(1)
    finally:
        if chat and chat.session_id and len(chat.messages) > 0:
            save_session(
                chat.session_id, chat.messages, chat.model, chat.provider_key, chat.metadata
            )
