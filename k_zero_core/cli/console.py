import sys

from k_zero_core.modes import MODE_REGISTRY
from k_zero_core.cli.menus import (
    choose_provider,
    manage_sessions, choose_mode, choose_io_mode, choose_main_experience, choose_workflow,
)
from k_zero_core.cli.io_setup import setup_io_handler
from k_zero_core.cli.session_setup import setup_chat_session
from k_zero_core.core.exceptions import APIVoiceException
from k_zero_core.core.plugin_loader import load_external_plugins
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.workflows.engine import WorkflowEngine, WorkflowPluginAdapter, WorkflowProviderError


def run_advanced_mode(
    *,
    mode_registry=None,
    choose_mode_func=choose_mode,
    choose_provider_func=choose_provider,
    choose_io_mode_func=choose_io_mode,
    manage_sessions_func=manage_sessions,
    setup_chat_session_func=setup_chat_session,
    setup_io_handler_func=setup_io_handler,
) -> None:
    """Ejecuta el flujo histórico basado en MODE_REGISTRY."""
    mode_registry = mode_registry or MODE_REGISTRY
    chat = None
    plugin = None
    mode_key = choose_mode_func()
    plugin = mode_registry[mode_key]()

    provider = choose_provider_func() if plugin.requires_llm else None

    if plugin.force_input_type:
        input_type = plugin.force_input_type
        output_type = "text"
        print(f"\n[Info] El modo '{plugin.get_name()}' forzará la entrada de {input_type}.")
    else:
        input_type, output_type = choose_io_mode_func()

    if plugin.requires_llm:
        session_id = manage_sessions_func()
        chat = setup_chat_session_func(plugin, provider, session_id)
    else:
        chat = None
        print(f"\n--- Iniciando {plugin.get_name()} ---")

    io_handler = setup_io_handler_func(input_type, output_type, plugin)

    try:
        plugin.run(chat, io_handler)
    except KeyboardInterrupt:
        print(f"\nSaliendo del Modo {plugin.get_name()}...")


def run_guided_workflow(
    workflow,
    *,
    workflow_engine=None,
    choose_mode_func=choose_mode,
    choose_provider_func=choose_provider,
    manage_sessions_func=manage_sessions,
    setup_chat_session_func=setup_chat_session,
    setup_io_handler_func=setup_io_handler,
) -> None:
    """Ejecuta un workflow guiado sin pasar por el menú de modos."""
    workflow_engine = workflow_engine or WorkflowEngine()
    plugin = WorkflowPluginAdapter(workflow)
    summary = workflow_engine.summarize(workflow)
    output_func = getattr(workflow_engine, "output_func", print)
    output_func(summary.message)
    provider = choose_provider_func() if workflow.requires_llm else None
    if provider is not None:
        workflow_engine.validate_provider(workflow, provider)
    chat = None
    if workflow.requires_llm:
        session_id = manage_sessions_func()
        chat = setup_chat_session_func(plugin, provider, session_id)
    elif workflow.mode_key:
        chat = ChatSession(provider=provider)
    io_handler = setup_io_handler_func(workflow.input_type.value, workflow.output_type.value, plugin)
    workflow_engine.run(
        workflow,
        chat_session=chat,
        io_handler=io_handler,
        provider=provider,
        summary=summary,
        show_summary=False,
    )


def run() -> None:
    """Main entry point for the CLI."""

    # 0. Cargar plugins dinámicos primero
    load_external_plugins()

    print("Bienvenido a Ollama CLI")

    try:
        experience = choose_main_experience()
        if experience == "guided":
            run_guided_workflow(choose_workflow())
        elif experience == "technical":
            from k_zero_core.cli.workflow_menus import run_workflow_studio

            run_workflow_studio()
        else:
            run_advanced_mode()

    except APIVoiceException as e:
        print(f"\nError de la aplicación: {e}")
        sys.exit(1)
    except WorkflowProviderError as e:
        print(f"\nError de workflow: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nSaliendo...")
    except Exception as e:
        print(f"\nOcurrió un error inesperado: {e}")
        sys.exit(1)
    finally:
        # Cada modo/workflow persiste su sesión durante la ejecución.
        pass
