"""Helpers compartidos para streaming, persistencia y salida de modos."""
from collections.abc import Callable, Iterable

from k_zero_core.audio.io_handler import IOHandler
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.storage.session_manager import save_session


TextWriter = Callable[[str], None]


def _print_text(text: str) -> None:
    print(text, end="", flush=True)


def stream_text_response(
    stream: Iterable[str],
    label: str,
    write: TextWriter = _print_text,
) -> str:
    """
    Imprime chunks de un stream con etiqueta y retorna la respuesta completa.

    Args:
        stream: Iterable de chunks de texto.
        label: Etiqueta visible antes del stream.
        write: Función de salida inyectable para pruebas.

    Returns:
        Texto completo acumulado.
    """
    response = ""
    write(f"\n[{label}]: ")
    for chunk in stream:
        write(chunk)
        response += chunk
    write("\n\n")
    return response


def save_and_output_response(
    chat_session: ChatSession,
    io_handler: IOHandler,
    response: str,
    user_text: str | None = None,
) -> None:
    """
    Persiste una respuesta del asistente y la envía por el canal de salida activo.

    Args:
        chat_session: Sesión activa.
        io_handler: Handler de I/O para TTS si aplica.
        response: Texto del asistente.
        user_text: Texto de usuario opcional a guardar antes de la respuesta.
    """
    if not response:
        return

    if user_text is not None:
        chat_session.add_user_message(user_text)
    chat_session.add_assistant_message(response)
    save_session(
        chat_session.session_id,
        chat_session.messages,
        chat_session.model,
        chat_session.provider_key,
        chat_session.metadata,
    )
    io_handler.output_response(response)
