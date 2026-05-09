"""
Modo Director Multi-Agente.
Orquesta a otros "roles" especializados para generar una respuesta consolidada.
"""
from collections.abc import Callable
from typing import Any, List

from k_zero_core.modes.base import BaseMode
from k_zero_core.modes.director_helpers import (
    ROLE_LABELS,
    ROLE_RESULT_HEADERS,
    ROLE_TOOLS,
    build_classifier_prompt,
    build_director_context,
    parse_roles,
)
from k_zero_core.modes.rag_helpers import restore_existing_rag_index
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.audio.io_handler import IOHandler

class DirectorMode(BaseMode):
    def get_name(self) -> str:
        return "Director Multi-Agente"

    def get_description(self) -> str:
        return "Orquesta a múltiples especialistas (Investigador, Analista, Técnico) según la consulta."

    def get_default_system_prompt(self) -> str:
        return (
            "Eres el Redactor Principal de un equipo multi-agente. Tu trabajo es leer la información "
            "recopilada por los especialistas y generar la respuesta final para el usuario. "
            "Sé claro, directo y sintetizado. No debes mencionar cómo obtuviste la información a menos "
            "que te pregunten. Habla directamente al usuario."
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
        print("Escribe 'salir', 'exit' o 'quit' (o dilo si usas micrófono) para terminar.\n")

        self.on_start(chat_session, io_handler)

        while True:
            user_text = io_handler.get_user_input()

            if not user_text:
                continue

            user_text_lower = user_text.lower().strip()
            if user_text_lower in ['salir', 'exit', 'quit']:
                print("\nConversación guardada. ¡Hasta luego!")
                break

            if io_handler.input_type == 'audio':
                print(f"Tú (Voz): {user_text}")

            print("Director clasificando requerimientos...", end="", flush=True)
            
            stream_clasif = chat_session.provider.stream_chat(
                chat_session.model, 
                [{"role": "user", "content": build_classifier_prompt(user_text)}]
            )
            roles_needed = "".join(list(stream_clasif)).lower()
            print(f"\n[Roles asignados: {roles_needed.strip()}]")
            
            # 2. Ejecutar Sub-Agentes
            sub_results: List[str] = []
            for role in parse_roles(roles_needed):
                label = ROLE_LABELS[role]
                print(f"  -> Ejecutando [{label}]...", end="", flush=True)
                res = self._run_sub_agent(
                    chat_session.provider,
                    chat_session.model,
                    label,
                    ROLE_TOOLS[role],
                    user_text,
                )
                sub_results.append(f"{ROLE_RESULT_HEADERS[role]}:\n{res}")
                print(" listo.")
                
            # 3. Redactor (Síntesis)
            contexto_extra = build_director_context(sub_results)
                
            # Agregamos la consulta original con el contexto secreto
            chat_session.add_user_message(user_text + contexto_extra)
            
            print(f"\n{chat_session.model} está redactando la respuesta... ")
            self._stream_and_respond(chat_session, io_handler, label="Director")
            
            # Limpiar el contexto para que la memoria no crezca infinitamente con datos repetidos
            chat_session.messages[-2] = {"role": "user", "content": user_text}
            
    def _run_sub_agent(
        self,
        provider: Any,
        model: str,
        role_name: str,
        tools: List[Callable],
        query: str,
    ) -> str:
        sys_prompt = f"Eres un {role_name}. Usa tus herramientas para resolver la consulta. Sé directo, solo entrega los datos encontrados sin saludos."
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": query}
        ]
        try:
            # Usamos el generador para ejecutar las tools silenciosamente
            stream = provider.stream_chat(model, messages, tools=tools)
            respuesta = "".join(list(stream))
            return respuesta
        except Exception as e:
            return f"Error en el especialista {role_name}: {str(e)}"
