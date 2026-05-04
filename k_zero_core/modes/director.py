"""
Modo Director Multi-Agente.
Orquesta a otros "roles" especializados para generar una respuesta consolidada.
"""
from typing import List, Optional

from k_zero_core.modes.base import BaseMode
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.audio.io_handler import IOHandler

# Importar tools
from k_zero_core.core.tools.web_search import buscar_en_internet, buscar_tavily
from k_zero_core.core.tools.web_reader import leer_pagina_web, extraer_wikipedia
from k_zero_core.core.tools.rag_search import buscar_en_documentos_locales
from k_zero_core.core.tools.analisis_json import analizar_valores_json
from k_zero_core.core.tools.matematica import calcular_matematica
from k_zero_core.core.tools.filesystem import leer_archivo, listar_directorio
from k_zero_core.core.tools.sistema import informacion_sistema
from k_zero_core.core.tools.date_time import obtener_hora_actual

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
        existing_collection_id = chat_session.metadata.get("rag_collection_id")
        existing_embedding_model = chat_session.metadata.get("rag_embedding_model")
        
        if existing_collection_id and existing_embedding_model:
            from k_zero_core.services.vector_store import VectorStore
            from k_zero_core.services.rag_engine import RagEngine
            from k_zero_core.core.tools.rag_search import set_active_rag
            
            engine = RagEngine(existing_embedding_model, VectorStore())
            if engine.is_indexed(existing_collection_id):
                set_active_rag(engine, existing_collection_id)
                print(f"📚 [Director]: Documento local detectado en la sesión (listo para consultar).")
            else:
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
            
            # 1. El Director decide roles
            clasificador_prompt = (
                f"La consulta del usuario es: '{user_text}'\n"
                "Selecciona CUALES de los siguientes especialistas necesitas invocar para recopilar datos.\n"
                "- investigador (busca en la web, extrae wikipedia, lee urls, busca en documentos).\n"
                "- analista (calcula matemáticas, extrae números de JSONs).\n"
                "- tecnico (lee archivos locales, lista carpetas, ve info del sistema/SO, hora).\n"
                "Responde ÚNICAMENTE con los nombres separados por coma en minúsculas (ej: investigador, tecnico). "
                "Si puedes responderlo directamente sin ayuda, responde: ninguno."
            )
            
            # Usar streaming y juntar la respuesta
            stream_clasif = chat_session.provider.stream_chat(
                chat_session.model, 
                [{"role": "user", "content": clasificador_prompt}]
            )
            roles_needed = "".join(list(stream_clasif)).lower()
            print(f"\n[Roles asignados: {roles_needed.strip()}]")
            
            # 2. Ejecutar Sub-Agentes
            sub_results = []
            
            if "investigador" in roles_needed:
                print("  -> Ejecutando [Investigador]...", end="", flush=True)
                tools_inv = [buscar_en_internet, buscar_tavily, leer_pagina_web, extraer_wikipedia, buscar_en_documentos_locales]
                res = self._run_sub_agent(chat_session.provider, chat_session.model, "Investigador", tools_inv, user_text)
                sub_results.append(f"DATOS DEL INVESTIGADOR:\n{res}")
                print(" listo.")
                
            if "analista" in roles_needed:
                print("  -> Ejecutando [Analista]...", end="", flush=True)
                tools_ana = [analizar_valores_json, calcular_matematica]
                res = self._run_sub_agent(chat_session.provider, chat_session.model, "Analista", tools_ana, user_text)
                sub_results.append(f"DATOS DEL ANALISTA:\n{res}")
                print(" listo.")
                
            if "tecnico" in roles_needed or "técnico" in roles_needed:
                print("  -> Ejecutando [Técnico]...", end="", flush=True)
                tools_tec = [leer_archivo, listar_directorio, informacion_sistema, obtener_hora_actual]
                res = self._run_sub_agent(chat_session.provider, chat_session.model, "Técnico", tools_tec, user_text)
                sub_results.append(f"DATOS DEL TÉCNICO:\n{res}")
                print(" listo.")
                
            # 3. Redactor (Síntesis)
            contexto_extra = ""
            if sub_results:
                contexto_extra = "\n\nAquí tienes la información recopilada por tu equipo:\n" + "\n\n".join(sub_results)
                
            # Agregamos la consulta original con el contexto secreto
            chat_session.add_user_message(user_text + contexto_extra)
            
            print(f"\n{chat_session.model} está redactando la respuesta... ")
            self._stream_and_respond(chat_session, io_handler, label="Director")
            
            # Limpiar el contexto para que la memoria no crezca infinitamente con datos repetidos
            chat_session.messages[-2] = {"role": "user", "content": user_text}
            
    def _run_sub_agent(self, provider, model, role_name, tools, query) -> str:
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
