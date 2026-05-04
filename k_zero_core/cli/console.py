import sys
from typing import Optional

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


def _setup_chat_session(plugin, provider, session_id: Optional[str]) -> ChatSession:
    """Configura y retorna la sesión de chat cargando historial o inicializando una nueva."""
    chat = ChatSession(session_id=session_id, provider=provider)

    if session_id:
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

    return chat


def _setup_io_handler(input_type: str, output_type: str, plugin) -> IOHandler:
    """Configura y retorna el IOHandler según el tipo de I/O, resolviendo imports de hardware perezosamente."""
    stt = None
    tts = None
    stt_config = {}

    if input_type == 'audio':
        from k_zero_core.audio.stt import SpeechTranscriber
        from k_zero_core.audio.config import WhisperConfig
        from k_zero_core.cli.menus import choose_stt_config
        
        stt_config = choose_stt_config()
        whisper_cfg = WhisperConfig.from_env()
        whisper_cfg.model_size = stt_config.get('model_size') or whisper_cfg.model_size
        whisper_cfg.language = stt_config.get('language')  # None = autodetect
        stt = SpeechTranscriber(config=whisper_cfg)

    if output_type == 'audio':
        from k_zero_core.audio.tts import TextToSpeech
        from k_zero_core.audio.config import TtsConfig
        
        tts_cfg = TtsConfig(voice=plugin.get_voice())
        tts = TextToSpeech(config=tts_cfg)

    return IOHandler(input_type, output_type, stt, tts, stt_config)


def run() -> None:
    """Main entry point for the CLI."""
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
            chat = _setup_chat_session(plugin, provider, session_id)
        else:
            chat = None
            print(f"\n--- Iniciando {plugin.get_name()} ---")

        # 5. Inicializar hardware de audio
        io_handler = _setup_io_handler(input_type, output_type, plugin)

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
