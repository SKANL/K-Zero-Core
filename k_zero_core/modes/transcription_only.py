import datetime

from k_zero_core.modes.base import AccumulatorMode
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.audio.io_handler import IOHandler
from k_zero_core.core.config import DATA_DIR

class TranscriptionOnlyMode(AccumulatorMode):
    """
    Modo que omite al agente de IA y simplemente guarda todo lo que el usuario 
    habla o escribe directamente a un archivo Markdown.
    """

    def get_name(self) -> str:
        return "Solo Transcribir (.md)"

    @property
    def requires_llm(self) -> bool:
        return False
        
    @property
    def force_input_type(self) -> str | None:
        return "audio"

    def get_description(self) -> str:
        return "Guarda todo lo que hablas directamente a un archivo sin usar IA."

    def get_default_system_prompt(self) -> str | None:
        return None

    def get_accumulation_prompt(self) -> str:
        return (
            "🎙️  Modo de transcripción continua iniciado.\n"
            "   Todo lo que digas se guardará en un archivo Markdown al terminar.\n"
            f"   Di o escribe '{self.get_stop_words()[0]}' para finalizar y guardar."
        )

    def process_accumulated(
        self,
        texts: list[str],
        chat_session: ChatSession,
        io_handler: IOHandler,
    ) -> None:
        if not texts:
            print("No se grabó ningún texto.")
            return

        texto_completo = "\n\n".join(texts)

        out_dir = DATA_DIR / "transcripciones"
        out_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcripcion_{timestamp}.md"
        filepath = out_dir / filename

        filepath.write_text(
            f"# Transcripción - {timestamp}\n\n{texto_completo}",
            encoding="utf-8",
        )

        print(f"\n✅ Transcripción guardada exitosamente en:\n   📁 {filepath.resolve()}\n")
