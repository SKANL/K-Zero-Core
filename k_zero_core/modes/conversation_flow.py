"""Constantes y helpers compartidos para loops conversacionales."""

EXIT_COMMANDS: tuple[str, ...] = ("salir", "exit", "quit")
ACCUMULATOR_STOP_WORDS: tuple[str, ...] = ("terminar", "guardar", "fin", *EXIT_COMMANDS)

EXIT_PROMPT_TEXT = "Escribe 'salir', 'exit' o 'quit' (o dilo si usas micrófono) para terminar.\n"
RAG_EXIT_PROMPT_TEXT = "Escribe 'salir', 'exit' o 'quit' para terminar.\n"


def normalize_command(text: str) -> str:
    """Normaliza texto de usuario para compararlo como comando."""
    return text.lower().strip()


def is_exit_command(text: str) -> bool:
    """Retorna True si el texto representa un comando de salida."""
    return normalize_command(text) in EXIT_COMMANDS
