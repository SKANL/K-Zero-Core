"""
Herramienta de búsqueda en base de datos vectorial local (Agentic RAG).
"""
from typing import Optional
from k_zero_core.services.rag_engine import RagEngine

# Variables globales para inyectar el motor RAG activo en la sesión
# Esto permite que la Tool sepa dónde buscar sin modificar la firma de la función (que es invocada por el LLM)
_active_rag_engine: Optional[RagEngine] = None
_active_collection_id: Optional[str] = None

def set_active_rag(engine: RagEngine, collection_id: str) -> None:
    """Configura el motor RAG activo para la sesión actual."""
    global _active_rag_engine, _active_collection_id
    _active_rag_engine = engine
    _active_collection_id = collection_id

def buscar_en_documentos_locales(query: str, top_k: int = 3) -> str:
    """
    Busca información en los documentos locales actualmente cargados en la memoria del agente.
    
    Args:
        query: La pregunta o concepto que quieres buscar en los documentos.
        top_k: Cantidad de fragmentos relevantes a retornar (por defecto 3).
        
    Returns:
        Fragmentos de los documentos que responden a la consulta, o un aviso si no hay documentos.
    """
    global _active_rag_engine, _active_collection_id
    
    if not _active_rag_engine or not _active_collection_id:
        return "No hay ningún documento local cargado en este momento en la sesión."
        
    try:
        resultados = _active_rag_engine.search(query, _active_collection_id, top_k=top_k)
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
