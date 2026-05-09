"""Preparación de documentos e índices para DocumentRAGMode."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from k_zero_core.modes.rag_helpers import (
    activate_rag_search,
    compute_collection_id,
    restore_existing_rag_index,
)
from k_zero_core.services.document_reader import extract_text, sanitize_path
from k_zero_core.services.rag_engine import RagEngine
from k_zero_core.services.vector_store import VectorStore


@dataclass(frozen=True)
class RagDocumentSetup:
    """Resultado de preparar un documento RAG para la sesión actual."""

    engine: RagEngine
    collection_id: str
    file_path: str


def _default_choose_embedding_model(provider: Any) -> str:
    from k_zero_core.cli.menus import choose_embedding_model

    return choose_embedding_model(provider)


def prepare_rag_document(
    chat_session: Any,
    io_handler: Any,
    *,
    vector_store: VectorStore | None = None,
    choose_embedding_model_func: Callable[[Any], str] = _default_choose_embedding_model,
    input_func: Callable[[str], str] = input,
    extract_text_func: Callable[[str], str] = extract_text,
    compute_collection_id_func: Callable[[str], str] = compute_collection_id,
    engine_cls: type = RagEngine,
    output_func: Callable[[str], None] = print,
) -> RagDocumentSetup:
    """Restaura o prepara el índice RAG asociado a una sesión CLI."""
    store = vector_store or VectorStore()

    restored = restore_existing_rag_index(chat_session.metadata, store)
    if restored:
        engine, collection_id, existing_file_path = restored
        output_func("📚 Índice vectorial encontrado. Documento listo para preguntas.")
        if existing_file_path:
            output_func(f"   Archivo: {existing_file_path}")
        output_func("")
        return RagDocumentSetup(engine, collection_id, existing_file_path)

    if chat_session.metadata.get("rag_collection_id") and chat_session.metadata.get("rag_embedding_model"):
        output_func("⚠️  El índice de esta sesión no se encontró en el vector store.")
        output_func("   Por favor, carga el documento de nuevo.\n")

    embedding_model = choose_embedding_model_func(chat_session.provider)

    output_func("\n--- Carga de Documento ---")
    while True:
        raw_path = input_func("Ingresa la ruta de tu archivo (PDF o TXT): ").strip()
        if not raw_path:
            continue
        file_path = sanitize_path(raw_path)

        try:
            output_func("Leyendo archivo...")
            text = extract_text_func(file_path)
            output_func(f"  Texto extraído: {len(text):,} caracteres")

            collection_id = compute_collection_id_func(file_path)
            engine = engine_cls(embedding_model, store)

            if engine.is_indexed(collection_id):
                output_func("✅ El documento ya estaba indexado. Reutilizando índice existente.")
            else:
                output_func("Indexando documento (esto solo ocurre la primera vez)...")
                total = engine.ingest(text, collection_id)
                output_func(f"✅ Documento indexado en {total} fragmentos.")

            activate_rag_search(engine, collection_id)
            chat_session.metadata.update({
                "rag_collection_id": collection_id,
                "rag_embedding_model": embedding_model,
                "rag_file_path": file_path,
            })

            output_func("\n¡Listo! ¿Qué quieres saber sobre el documento?\n")
            if io_handler is not None:
                io_handler.output_response("Documento listo. ¿Qué quieres saber?")
            return RagDocumentSetup(engine, collection_id, file_path)

        except Exception as e:
            output_func(f"Error: {e}\nIntenta de nuevo.\n")
