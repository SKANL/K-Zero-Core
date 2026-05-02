import sys

from k_zero_core.modes import MODE_REGISTRY
from k_zero_core.cli.menus import (
    choose_provider, choose_model, choose_system_prompt,
    manage_sessions, choose_mode, choose_io_mode,
)
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.services.providers import get_provider
from k_zero_core.storage.session_manager import load_session, save_session
from k_zero_core.core.exceptions import APIVoiceException
from k_zero_core.audio.io_handler import IOHandler


def run() -> None:
    """Main entry point for the CLI."""
    print("Bienvenido a Ollama CLI")

    chat = None
    plugin = None

    try:
        # 1. Elegir proveedor de IA (se omite el menú si solo hay uno)
        provider = choose_provider()

        # 2. Elegir modo de interacción
        mode_key = choose_mode()
        plugin = MODE_REGISTRY[mode_key]()

        # 3. Elegir estrategia de I/O
        input_type, output_type = choose_io_mode()

        # 4. Gestionar sesiones
        session_id = manage_sessions()
        chat = ChatSession(session_id=session_id, provider=provider)

        if session_id:
            # Reanudar sesión — restaurar modelo y proveedor guardados
            session_data = load_session(session_id)
            saved_provider_key = session_data.get("provider", "ollama")

            # Si el proveedor guardado difiere del seleccionado, respetar el guardado
            if saved_provider_key != provider.key:
                chat.provider = get_provider(saved_provider_key)
                print(f"(Restaurando proveedor '{saved_provider_key}' de la sesión guardada)")

            chat.model = session_data.get("model", "")
            chat.metadata = session_data.get("metadata", {})
            chat.load_history(session_data.get("messages", []))
            print(f"\nRetomando sesión con {chat.model} ({chat.provider.get_display_name()}) en modo {plugin.get_name()}...")
        else:
            # Nueva sesión
            chat.model = choose_model(provider)

            print("\n(Opcional) Puedes elegir un System Prompt guardado, o usar el que viene por defecto para este Modo.")
            sys_prompt = choose_system_prompt(plugin.get_default_system_prompt() or "")

            if sys_prompt:
                chat.set_system_prompt(sys_prompt)
                print("System prompt personalizado cargado.")
            else:
                default_prompt = plugin.get_default_system_prompt()
                if default_prompt:
                    chat.set_system_prompt(default_prompt)
                    print("System prompt por defecto del modo cargado.")

            print(f"\n--- Iniciando nuevo chat con {chat.model} ({chat.provider.get_display_name()}) ---")

        # 5. Inicializar hardware de audio solo si es necesario
        stt = None
        tts = None
        if input_type == 'audio':
            from k_zero_core.audio.stt import SpeechTranscriber
            stt = SpeechTranscriber()
        if output_type == 'audio':
            from k_zero_core.audio.tts import TextToSpeech
            tts = TextToSpeech(default_voice=plugin.get_voice())

        io_handler = IOHandler(input_type, output_type, stt, tts)

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
