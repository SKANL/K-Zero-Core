"""
Modo de interrogación de documentos usando RAG (Retrieval-Augmented Generation) semántico.

Pipeline:
    1. on_start() → elegir embedding model → cargar documento → indexar en ChromaDB
    2. run() → por cada pregunta: búsqueda semántica → inyección efímera de contexto → LLM

Diferencia clave vs. "full-text stuffing":
    - El documento completo NO se mete en el contexto
    - Solo se inyectan los N chunks más relevantes por pregunta
    - El historial de sesión guarda Q&A limpios (sin el bloque de contexto)
    - El índice vectorial persiste en disco → no re-indexar al reanudar sesión
"""
from k_zero_core.modes.base import BaseMode
from k_zero_core.modes.conversation_flow import RAG_EXIT_PROMPT_TEXT, is_exit_command
from k_zero_core.modes.mode_streaming import save_and_output_response, stream_text_response
from k_zero_core.modes.rag_helpers import build_rag_messages
from k_zero_core.modes.rag_setup import prepare_rag_document
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.audio.io_handler import IOHandler


class DocumentRAGMode(BaseMode):
    """
    Modo de interrogación semántica de documentos PDF y TXT.

    Usa ChromaDB como vector store persistente y nomic-embed (o cualquier modelo
    de embedding disponible) para generar embeddings. Soporta documentos de cualquier
    tamaño sin límite de caracteres.
    """

    TOP_K_CHUNKS = 3  # número de fragmentos relevantes a inyectar por pregunta

    def get_name(self) -> str:
        return "Interrogar Documento (RAG Local)"

    def get_description(self) -> str:
        return "Carga un PDF o TXT y haz preguntas precisas. Usa búsqueda semántica — sin límite de tamaño."

    def get_default_system_prompt(self) -> str:
        return (
            "Eres un analista de documentos experto. "
            "Recibirás fragmentos relevantes de un documento y responderás preguntas "
            "basándote ÚNICAMENTE en esa información. "
            "Si la respuesta no está en los fragmentos proporcionados, dilo claramente."
        )

    def get_tools(self):
        """RAG no usa herramientas de agente."""
        return None

    def on_start(self, chat_session: ChatSession, io_handler: IOHandler) -> None:
        """
        Inicializa el RagEngine. Si la sesión ya tiene un índice vectorial guardado
        y este existe en ChromaDB, lo reutiliza directamente sin re-indexar.
        """
        setup = prepare_rag_document(chat_session, io_handler)
        self._rag_engine = setup.engine
        self._collection_id = setup.collection_id

    def run(self, chat_session: ChatSession, io_handler: IOHandler) -> None:
        """
        Loop conversacional RAG. Por cada pregunta:
        1. Búsqueda semántica de chunks relevantes en ChromaDB
        2. Construcción de mensajes efímeros (contexto + pregunta) para la llamada LLM
        3. El LLM responde solo con los fragmentos relevantes como contexto
        4. Se guarda en historial solo el Q&A limpio (sin el bloque de contexto repetido)
        """
        print(f"\n--- Modo Activado: {self.get_name()} ---")
        print(RAG_EXIT_PROMPT_TEXT)

        self.on_start(chat_session, io_handler)

        while True:
            user_text = io_handler.get_user_input()

            if not user_text:
                continue

            if is_exit_command(user_text):
                print("\n¡Hasta luego!")
                break

            if io_handler.input_type == 'audio':
                print(f"Tú (Voz): {user_text}")

            relevant_chunks = self._rag_engine.search(
                user_text, self._collection_id, top_k=self.TOP_K_CHUNKS
            )

            if not relevant_chunks:
                print("\n[RAG]: No encontré información relevante en el documento para esa pregunta.\n")
                continue

            messages_for_call = build_rag_messages(
                chat_session.messages, relevant_chunks, user_text
            )

            print(f"{chat_session.model} está pensando... ", end="", flush=True)

            stream = chat_session.provider.stream_chat(
                chat_session.model, messages_for_call
            )

            respuesta_completa = stream_text_response(stream, "RAG Respuesta")

            save_and_output_response(
                chat_session, io_handler, respuesta_completa, user_text=user_text
            )
