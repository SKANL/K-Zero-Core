import datetime
from typing import List

from k_zero_core.modes.base import AccumulatorMode
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.audio.io_handler import IOHandler
from k_zero_core.core.config import DATA_DIR


class BrainDumpMode(AccumulatorMode):
    """
    Modo Secretario: acumula todo lo que el usuario dice y, al recibir
    la palabra clave, genera un archivo Markdown con un resumen organizado
    y lista de tareas.
    """

    def get_name(self) -> str:
        return "Secretario (Brain Dump)"

    def get_description(self) -> str:
        return "Tú hablas, él escucha y al final te genera un resumen organizado y una lista de tareas."

    def get_default_system_prompt(self) -> str:
        return (
            "Eres un secretario organizador experto. Recibirás un volcado de pensamientos (brain dump) desestructurado. "
            "Tu objetivo es leerlo todo y extraer la información clave, generando un archivo Markdown con: "
            "1. Un breve resumen de los temas mencionados. "
            "2. Una lista estructurada de 'Tareas por hacer' (To-Dos). "
            "3. Cualquier idea creativa o punto clave destacado. "
            "No saludes, devuelve directamente el contenido en formato Markdown."
        )

    def get_accumulation_prompt(self) -> str:
        return "Empieza a hablar o escribir todo lo que tienes en la cabeza."

    def process_accumulated(
        self,
        texts: List[str],
        chat_session: ChatSession,
        io_handler: IOHandler,
    ) -> None:
        """
        Envía todo el texto acumulado al modelo vía el proveedor activo y guarda
        la respuesta organizada como un archivo Markdown en el directorio de datos.
        """
        if not texts:
            print("No anotaste nada. ¡Hasta luego!")
            return

        texto_final = " ".join(texts)
        chat_session.add_user_message(texto_final)

        print(f"{chat_session.model} está organizando tus ideas... ", end="", flush=True)

        # Acumular silenciosamente — el resultado va a archivo, no a pantalla
        stream = chat_session.provider.stream_chat(chat_session.model, chat_session.messages)
        respuesta_completa = "".join(stream)

        print("\n")

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = DATA_DIR / f"braindump_{timestamp}.md"
        filename.write_text(respuesta_completa, encoding="utf-8")

        print(f"¡Listo! Notas guardadas en: {filename}")
        io_handler.output_response("Tus notas han sido guardadas con éxito.")
