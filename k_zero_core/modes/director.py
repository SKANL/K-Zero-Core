"""Modo Director Multi-Agente."""

from k_zero_core.modes.base import BaseMode
from k_zero_core.modes.conversation_flow import EXIT_PROMPT_TEXT, is_exit_command
from k_zero_core.modes.rag_helpers import restore_existing_rag_index
from k_zero_core.services.director_engine import DirectorEngine
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.audio.io_handler import IOHandler
from k_zero_core.storage.memory_manager import TodoStore
from k_zero_core.storage.session_manager import save_session

class DirectorMode(BaseMode):
    def __init__(self) -> None:
        self._director_engine = DirectorEngine()

    def get_name(self) -> str:
        return "Director Multi-Agente"

    def get_description(self) -> str:
        return "Orquesta a múltiples especialistas (Investigador, Analista, Técnico) según la consulta."

    def get_default_system_prompt(self) -> str:
        return (
            "Eres el Redactor Principal de un equipo multi-agente. Tu trabajo es leer la información "
            "recopilada por los especialistas y generar la respuesta final para el usuario. "
            "Sé claro, directo y sintetizado. Si el contexto contiene resultados como 'Archivo creado:' "
            "o 'Copia editada:', incluye esas rutas exactas en la respuesta final. No digas que no tienes "
            "acceso a archivos locales cuando una herramienta ya accedió o escribió archivos. Si una edición "
            "solicitada no se hizo, dilo como limitación concreta. No debes mencionar cómo obtuviste la "
            "información a menos que te pregunten. Habla directamente al usuario."
        )

    def on_start(self, chat_session: ChatSession, io_handler: IOHandler) -> None:
        """
        Al iniciar el modo, verifica si la sesión actual tiene un índice RAG asociado.
        Si es así, levanta el motor RAG silenciosamente para que el sub-agente Investigador
        pueda usarlo sin necesidad de pasar por el Modo RAG.
        """
        from k_zero_core.services.vector_store import VectorStore

        restored = restore_existing_rag_index(chat_session.metadata, VectorStore())
        if restored:
            print(f"📚 [Director]: Documento local detectado en la sesión (listo para consultar).")
        elif chat_session.metadata.get("rag_collection_id") and chat_session.metadata.get("rag_embedding_model"):
            print("⚠️ [Director]: Se detectó un documento en la sesión, pero el índice no existe en la base de datos.")

    def run(self, chat_session: ChatSession, io_handler: IOHandler) -> None:
        """Override del loop principal para inyectar lógica de orquestación."""
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

            print("Director clasificando requerimientos...", end="", flush=True)

            director_engine = DirectorEngine(
                max_workers=self._director_engine.max_workers,
                todo_store=TodoStore(),
                session_id=chat_session.session_id,
            )
            result = director_engine.collect(
                chat_session.provider,
                chat_session.model,
                user_text,
                classify=True,
            )
            roles = result.roles
            print(f"\n[Roles asignados: {', '.join(roles) if roles else 'ninguno'}]")

            if roles:
                from k_zero_core.modes.director_helpers import ROLE_DEFINITIONS

                labels = ", ".join(ROLE_DEFINITIONS[role].label for role in roles)
                print(f"  -> Ejecutando especialistas en paralelo: {labels}...", end="", flush=True)
                print(" listo.")
                
            # 3. Redactor (Síntesis)
            contexto_extra = result.context
            if "FUENTES REQUERIDAS:" in contexto_extra:
                message = contexto_extra.strip()
                print(f"\n[Director]: {message}\n")
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
                continue
                
            # Agregamos la consulta original con el contexto secreto
            chat_session.add_user_message(user_text + contexto_extra)
            
            print(f"\n{chat_session.model} está redactando la respuesta... ")
            self._stream_and_respond(chat_session, io_handler, label="Director")
            
            # Limpiar el contexto para que la memoria no crezca infinitamente con datos repetidos
            chat_session.messages[-2] = {"role": "user", "content": user_text}
            save_session(
                chat_session.session_id,
                chat_session.messages,
                chat_session.model,
                chat_session.provider_key,
                chat_session.metadata,
            )
            self._maybe_offer_memory(chat_session, io_handler, user_text)
            
