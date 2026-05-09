from abc import ABC, abstractmethod
from typing import Optional, List

from k_zero_core.services.chat_session import ChatSession
from k_zero_core.audio.io_handler import IOHandler
from k_zero_core.modes.conversation_flow import (
    ACCUMULATOR_STOP_WORDS,
    EXIT_PROMPT_TEXT,
    is_exit_command,
    normalize_command,
)
from k_zero_core.modes.mode_streaming import save_and_output_response, stream_text_response


class BaseMode(ABC):
    """Abstract base class for all CLI Modes using the Template Method pattern."""

    @abstractmethod
    def get_name(self) -> str:
        """Return the display name of the mode."""
        pass

    @property
    def requires_llm(self) -> bool:
        """Determina si este modo interactúa con un LLM."""
        return True
        
    @property
    def force_input_type(self) -> Optional[str]:
        """Fuerza un tipo de entrada específico ('audio' o 'text'). None si es libre."""
        return None

    @abstractmethod
    def get_description(self) -> str:
        """Return a short description of the mode."""
        pass

    @abstractmethod
    def get_default_system_prompt(self) -> Optional[str]:
        """Return the fallback/default system prompt for this mode, if any."""
        pass

    def get_voice(self) -> str:
        """Return the default voice ID for this mode."""
        return "es-MX-DaliaNeural"

    def get_tools(self) -> Optional[list]:
        """Return a list of python functions to be used as tools by the model."""
        from k_zero_core.core.tools import get_all_tools
        return get_all_tools()

    def on_start(self, chat_session: ChatSession, io_handler: IOHandler) -> None:
        """Optional hook to execute logic before the main loop starts."""
        pass

    def _stream_and_respond(
        self,
        chat_session: ChatSession,
        io_handler: IOHandler,
        label: str = "Respuesta",
        tools: Optional[list] = None,
    ) -> str:
        """
        Streams a response from the active AI provider for the current chat session,
        prints it in real time, persists the session, and triggers TTS if enabled.

        Args:
            chat_session: The active chat session (messages must already include the user turn).
            io_handler: The I/O handler that manages audio output.
            label: Display label printed before the response (e.g. "Narrador", "Respuesta").
            tools: Optional list of callable tools for the agent.

        Returns:
            The complete assistant response as a string.
        """
        stream = chat_session.provider.stream_chat(
            chat_session.model, chat_session.messages, tools=tools
        )
        response = stream_text_response(stream, label)
        save_and_output_response(chat_session, io_handler, response)
        return response

    def run(self, chat_session: ChatSession, io_handler: IOHandler) -> None:
        """The main interaction loop (Template Method)."""
        print(f"\n--- Modo Activado: {self.get_name()} ---")
        print(EXIT_PROMPT_TEXT)

        self.on_start(chat_session, io_handler)

        while True:
            user_text = io_handler.get_user_input()

            if not user_text:
                continue

            if is_exit_command(user_text):
                print("\nConversación guardada. ¡Hasta luego!")
                break

            if io_handler.input_type == 'audio':
                print(f"Tú (Voz): {user_text}")

            chat_session.add_user_message(user_text)

            print(f"{chat_session.model} está pensando... ", end="", flush=True)
            tools = self.get_tools()
            self._stream_and_respond(chat_session, io_handler, tools=tools)


class AccumulatorMode(BaseMode):
    """
    Abstract base for modes that accumulate all user inputs before processing them.

    Instead of responding after each message, these modes collect every input
    into a list until the user says a stop word, then call `process_accumulated()`
    with the full list. This enables batch-processing workflows like Brain Dump,
    meeting transcription, interview recording, etc.

    Subclasses must implement:
        - get_name(), get_description(), get_default_system_prompt()  (from BaseMode)
        - process_accumulated(texts, chat_session, io_handler)

    Subclasses may override:
        - get_stop_words()           → list of trigger words to end accumulation
        - get_accumulation_prompt()  → instructions shown at loop start
    """

    def get_stop_words(self) -> List[str]:
        """Words/phrases that trigger end of accumulation (case-insensitive)."""
        return list(ACCUMULATOR_STOP_WORDS)

    def get_accumulation_prompt(self) -> str:
        """Return the instruction message shown to the user at the start of the loop."""
        return (
            "Empieza a escribir o hablar. "
            f"Di '{self.get_stop_words()[0]}' cuando hayas terminado."
        )

    @abstractmethod
    def process_accumulated(
        self,
        texts: List[str],
        chat_session: ChatSession,
        io_handler: IOHandler,
    ) -> None:
        """
        Called once with all accumulated user inputs after a stop word is detected.

        Args:
            texts: All non-empty user inputs collected during the accumulation loop.
            chat_session: The active chat session to use for model calls.
            io_handler: The I/O handler for audio output.
        """
        pass

    def run(self, chat_session: ChatSession, io_handler: IOHandler) -> None:
        """Accumulation loop: collect inputs until stop word, then process."""
        stop_words = self.get_stop_words()

        print(f"\n--- Modo Activado: {self.get_name()} ---")
        print(self.get_accumulation_prompt())
        print(f"Palabras clave para finalizar: {', '.join(stop_words)}\n")

        self.on_start(chat_session, io_handler)

        acumulado: List[str] = []

        while True:
            user_text = io_handler.get_user_input()

            if not user_text:
                continue

            if normalize_command(user_text) in stop_words:
                print("\nProcesando todo lo que dijiste...")
                break

            if io_handler.input_type == 'audio':
                print(f"-> {user_text}")

            acumulado.append(user_text)

        self.process_accumulated(acumulado, chat_session, io_handler)
