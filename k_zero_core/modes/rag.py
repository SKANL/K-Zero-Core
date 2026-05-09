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
from k_zero_core.modes.mode_streaming import save_and_output_response, stream_text_response
from k_zero_core.modes.rag_helpers import (
    activate_rag_search,
    build_rag_messages,
    compute_collection_id,
    restore_existing_rag_index,
)
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.audio.io_handler import IOHandler
from k_zero_core.services.document_reader import extract_text, sanitize_path
from k_zero_core.services.vector_store import VectorStore
from k_zero_core.services.rag_engine import RagEngine


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
        vector_store = VectorStore()

        restored = restore_existing_rag_index(chat_session.metadata, vector_store)
        if restored:
            self._rag_engine, self._collection_id, existing_file_path = restored
            print(f"📚 Índice vectorial encontrado. Documento listo para preguntas.")
            if existing_file_path:
                print(f"   Archivo: {existing_file_path}")
            print()
            return

        if chat_session.metadata.get("rag_collection_id") and chat_session.metadata.get("rag_embedding_model"):
            print("⚠️  El índice de esta sesión no se encontró en el vector store.")
            print("   Por favor, carga el documento de nuevo.\n")

        # Primera vez o índice perdido → elegir embedding model y cargar documento
        from k_zero_core.cli.menus import choose_embedding_model
        embedding_model = choose_embedding_model(chat_session.provider)

        print("\n--- Carga de Documento ---")
        while True:
            raw_path = input("Ingresa la ruta de tu archivo (PDF o TXT): ").strip()
            if not raw_path:
                continue
            file_path = sanitize_path(raw_path)

            try:
                print("Leyendo archivo...")
                texto = extract_text(file_path)
                print(f"  Texto extraído: {len(texto):,} caracteres")

                collection_id = compute_collection_id(file_path)
                engine = RagEngine(embedding_model, vector_store)

                if engine.is_indexed(collection_id):
                    print("✅ El documento ya estaba indexado. Reutilizando índice existente.")
                else:
                    print("Indexando documento (esto solo ocurre la primera vez)...")
                    total = engine.ingest(texto, collection_id)
                    print(f"✅ Documento indexado en {total} fragmentos.")

                self._rag_engine = engine
                self._collection_id = collection_id

                activate_rag_search(engine, collection_id)

                # Persistir metadata para poder recuperar el índice al reanudar sesión
                chat_session.metadata.update({
                    "rag_collection_id": collection_id,
                    "rag_embedding_model": embedding_model,
                    "rag_file_path": file_path,
                })

                print("\n¡Listo! ¿Qué quieres saber sobre el documento?\n")
                io_handler.output_response("Documento listo. ¿Qué quieres saber?")
                break

            except Exception as e:
                print(f"Error: {e}\nIntenta de nuevo.\n")

    def run(self, chat_session: ChatSession, io_handler: IOHandler) -> None:
        """
        Loop conversacional RAG. Por cada pregunta:
        1. Búsqueda semántica de chunks relevantes en ChromaDB
        2. Construcción de mensajes efímeros (contexto + pregunta) para la llamada LLM
        3. El LLM responde solo con los fragmentos relevantes como contexto
        4. Se guarda en historial solo el Q&A limpio (sin el bloque de contexto repetido)
        """
        print(f"\n--- Modo Activado: {self.get_name()} ---")
        print("Escribe 'salir', 'exit' o 'quit' para terminar.\n")

        self.on_start(chat_session, io_handler)

        while True:
            user_text = io_handler.get_user_input()

            if not user_text:
                continue

            if user_text.lower().strip() in ['salir', 'exit', 'quit']:
                print("\n¡Hasta luego!")
                break

            if io_handler.input_type == 'audio':
                print(f"Tú (Voz): {user_text}")

            # 1. Búsqueda semántica — encuentra los chunks más relevantes
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

            # 3. Llamada al LLM con contexto efímero
            stream = chat_session.provider.stream_chat(
                chat_session.model, messages_for_call
            )

            respuesta_completa = stream_text_response(stream, "RAG Respuesta")

            # 4. Solo Q&A limpio en el historial de sesión
            save_and_output_response(
                chat_session, io_handler, respuesta_completa, user_text=user_text
            )
