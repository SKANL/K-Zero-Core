"""Helpers internos para mantener DocumentRAGMode enfocado en el flujo CLI."""
import hashlib
from pathlib import Path
from typing import Any

from k_zero_core.services.rag_engine import RagEngine
from k_zero_core.services.vector_store import VectorStore

RAG_CONTEXT_SEPARATOR = "\n\n---\n\n"
RAG_CONTEXT_HEADER = "[Fragmentos relevantes del documento]"
RAG_QUESTION_HEADER = "[Pregunta del usuario]"


def compute_collection_id(file_path: str) -> str:
    """
    Genera un ID estable de colección ChromaDB basado en el contenido del archivo.
    """
    content = Path(file_path).read_bytes()
    sha = hashlib.sha256(content).hexdigest()
    return f"doc-{sha[:24]}"


def build_rag_messages(
    history: list[dict[str, Any]],
    relevant_chunks: list[str],
    user_text: str,
) -> list[dict[str, Any]]:
    """
    Construye mensajes efímeros con contexto RAG sin mutar el historial limpio.
    """
    context_block = RAG_CONTEXT_SEPARATOR.join(relevant_chunks)
    return list(history) + [
        {
            "role": "user",
            "content": (
                f"{RAG_CONTEXT_HEADER}\n\n"
                f"{context_block}\n\n"
                f"{RAG_QUESTION_HEADER}\n{user_text}"
            ),
        }
    ]


def activate_rag_search(engine: RagEngine, collection_id: str) -> None:
    """Inyecta el motor RAG activo en la tool de búsqueda local."""
    from k_zero_core.core.tools.rag_search import set_active_rag

    set_active_rag(engine, collection_id)


def restore_existing_rag_index(
    metadata: dict[str, Any],
    vector_store: VectorStore,
) -> tuple[RagEngine, str, str] | None:
    """
    Recupera un índice RAG persistido si la sesión tiene metadata válida.

    Returns:
        Tupla (engine, collection_id, file_path) si existe, o None.
    """
    collection_id = metadata.get("rag_collection_id")
    embedding_model = metadata.get("rag_embedding_model")
    file_path = metadata.get("rag_file_path", "")

    if not collection_id or not embedding_model:
        return None

    engine = RagEngine(embedding_model, vector_store)
    if not engine.is_indexed(collection_id):
        return None

    activate_rag_search(engine, collection_id)
    return engine, collection_id, file_path
