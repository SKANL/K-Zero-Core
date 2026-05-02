from k_zero_core.modes.base import BaseMode
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.audio.io_handler import IOHandler


class DungeonMasterMode(BaseMode):
    def get_name(self) -> str:
        return "Dungeon Master (Juego de Rol Interactivo)"

    def get_description(self) -> str:
        return "Juega una partida de D&D o historia interactiva. Relatas tus acciones y el narrador responde."

    def get_default_system_prompt(self) -> str:
        return (
            "Eres el Dungeon Master (Narrador) de una aventura de rol interactiva de fantasía épica. "
            "El usuario es el héroe principal. Describe el entorno, los eventos y las consecuencias de las acciones "
            "del usuario de manera vívida y emocionante, pero sin exagerar en longitud. "
            "No tomes decisiones por el jugador. Siempre termina tus respuestas preguntando: '¿Qué haces?' o '¿Qué decides hacer?'. "
            "Tus respuestas deben estar diseñadas para ser leídas en voz alta."
        )

    def get_voice(self) -> str:
        return "es-ES-AlvaroNeural"

    def on_start(self, chat_session: ChatSession, io_handler: IOHandler) -> None:
        """Si es una sesión nueva, el DM arranca la historia automáticamente."""
        is_new_session = not any(m['role'] != 'system' for m in chat_session.messages)
        if is_new_session:
            print("El Narrador está preparando la historia...")
            chat_session.add_user_message(
                "Comienza la aventura. Descríbeme en dónde estoy y preséntame el primer desafío."
            )
            self._stream_and_respond(chat_session, io_handler, label="Narrador")
