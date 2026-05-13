from abc import ABC, abstractmethod

from k_zero_core.services.chat_session import ChatSession
from k_zero_core.audio.io_handler import IOHandler
from k_zero_core.modes.conversation_flow import (
    ACCUMULATOR_STOP_WORDS,
    EXIT_PROMPT_TEXT,
    is_exit_command,
    normalize_command,
)
from k_zero_core.modes.mode_streaming import save_and_output_response, stream_text_response
from k_zero_core.services.memory_reflection import MemoryReflectionService
from k_zero_core.storage.memory_manager import TodoStore
from k_zero_core.storage.session_manager import save_session


class BaseMode(ABC):
    """Abstract base class for all CLI Modes using the Template Method pattern."""

    @abstractmethod
    def get_name(self) -> str:
        """Return the display name of the mode."""

    @property
    def requires_llm(self) -> bool:
        """Determina si este modo interactúa con un LLM."""
        return True
        
    @property
    def force_input_type(self) -> str | None:
        """Fuerza un tipo de entrada específico ('audio' o 'text'). None si es libre."""
        return None

    @abstractmethod
    def get_description(self) -> str:
        """Return a short description of the mode."""

    @abstractmethod
    def get_default_system_prompt(self) -> str | None:
        """Return the fallback/default system prompt for this mode, if any."""

    def get_voice(self) -> str:
        """Return the default voice ID for this mode."""
        return "es-MX-DaliaNeural"

    def get_tools(self) -> list | None:
        """Return a list of python functions to be used as tools by the model."""
        from k_zero_core.core.tools import get_all_tools
        return get_all_tools()

    def get_memory_reflection_service(self) -> MemoryReflectionService:
        """Servicio interno para confirmar y proponer memoria persistente."""
        return MemoryReflectionService()

    def get_todo_store(self) -> TodoStore:
        """Store interno de tareas por sesión."""
        return TodoStore()

    def on_start(self, chat_session: ChatSession, io_handler: IOHandler) -> None:
        """Optional hook to execute logic before the main loop starts."""

    def _stream_and_respond(
        self,
        chat_session: ChatSession,
        io_handler: IOHandler,
        label: str = "Respuesta",
        tools: list | None = None,
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

    def _handle_memory_confirmation(self, chat_session: ChatSession, io_handler: IOHandler, user_text: str) -> bool:
        """Procesa confirmación explícita de memoria pendiente sin invocar al LLM."""
        result = self.get_memory_reflection_service().confirm_if_requested(chat_session, user_text)
        if result is None:
            return False

        message = result.message
        print(f"\n{message}")
        chat_session.add_user_message(user_text)
        chat_session.add_assistant_message(message)
        save_session(
            chat_session.session_id,
            chat_session.messages,
            chat_session.model,
            chat_session.provider_key,
            chat_session.metadata,
        )
        io_handler.output_response(message)
        return True

    def _maybe_offer_memory(self, chat_session: ChatSession, io_handler: IOHandler, user_text: str) -> None:
        """Propone memoria persistente después de responder, sin guardarla aún."""
        proposal = self.get_memory_reflection_service().consider_user_message(chat_session, user_text)
        if not proposal:
            return
        print(f"\n{proposal}")
        chat_session.add_assistant_message(proposal)
        save_session(
            chat_session.session_id,
            chat_session.messages,
            chat_session.model,
            chat_session.provider_key,
            chat_session.metadata,
        )
        io_handler.output_response(proposal)

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

            if self._handle_memory_confirmation(chat_session, io_handler, user_text):
                continue

            chat_session.add_user_message(user_text)

            print(f"{chat_session.model} está pensando... ", end="", flush=True)
            tools = self.get_tools()
            self._stream_and_respond(chat_session, io_handler, tools=tools)
            self._maybe_offer_memory(chat_session, io_handler, user_text)


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

    def get_stop_words(self) -> list[str]:
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
        texts: list[str],
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

    def run(self, chat_session: ChatSession, io_handler: IOHandler) -> None:
        """Accumulation loop: collect inputs until stop word, then process."""
        stop_words = self.get_stop_words()

        print(f"\n--- Modo Activado: {self.get_name()} ---")
        print(self.get_accumulation_prompt())
        print(f"Palabras clave para finalizar: {', '.join(stop_words)}\n")

        self.on_start(chat_session, io_handler)

        acumulado: list[str] = []

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

        todo_store = self.get_todo_store()
        task_id = f"{self.get_name().lower().replace(' ', '_')}_process"
        if acumulado:
            todo_store.set_plan(chat_session.session_id, [(task_id, f"Procesar {self.get_name()}")])
            todo_store.update_status(chat_session.session_id, task_id, "running")
        try:
            self.process_accumulated(acumulado, chat_session, io_handler)
        except Exception:
            if acumulado:
                todo_store.update_status(chat_session.session_id, task_id, "blocked")
            raise
        if acumulado:
            todo_store.update_status(chat_session.session_id, task_id, "done")
