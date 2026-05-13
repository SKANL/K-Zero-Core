"""
Herramienta de búsqueda en base de datos vectorial local (Agentic RAG).
"""
from dataclasses import dataclass

from k_zero_core.services.rag_engine import RagEngine


@dataclass
class _ActiveRAGContext:
    """Estado RAG activo para la sesión CLI actual."""

    engine: RagEngine | None = None
    collection_id: str | None = None

    @property
    def is_ready(self) -> bool:
        return self.engine is not None and self.collection_id is not None


# Contexto global intencional: la tool debe mantener una firma simple invocable por el LLM.
_active_context = _ActiveRAGContext()


def set_active_rag(engine: RagEngine, collection_id: str) -> None:
    """Configura el motor RAG activo para la sesión actual."""
    _active_context.engine = engine
    _active_context.collection_id = collection_id


def buscar_en_documentos_locales(query: str, top_k: int = 3) -> str:
    """
    Busca información en los documentos locales actualmente cargados en la memoria del agente.
    
    Args:
        query: La pregunta o concepto que quieres buscar en los documentos.
        top_k: Cantidad de fragmentos relevantes a retornar (por defecto 3).
        
    Returns:
        Fragmentos de los documentos que responden a la consulta, o un aviso si no hay documentos.
    """
    if not _active_context.is_ready:
        return "No hay ningún documento local cargado en este momento en la sesión."
        
    try:
        assert _active_context.engine is not None
        assert _active_context.collection_id is not None
        resultados = _active_context.engine.search(
            query,
            _active_context.collection_id,
            top_k=top_k,
        )
        if not resultados:
            return "No se encontró información relevante en el documento para esta consulta."
            
        salida = [f"Resultados de documentos locales para '{query}':\n"]
        for i, res in enumerate(resultados):
            salida.append(f"--- Fragmento {i+1} ---")
            salida.append(res)
            salida.append("")
            
        return "\n".join(salida)
    except Exception as e:
        return f"Error al buscar en documentos: {str(e)}"
