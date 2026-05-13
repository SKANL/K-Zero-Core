"""
Wrapper sobre ChromaDB PersistentClient para almacenar y buscar embeddings de documentos.

Usa embeddings pre-computados (provistos por Ollama) en lugar del sistema de
embedding interno de ChromaDB. Los datos se persisten en VECTOR_STORE_DIR.
"""
import logging

import chromadb

from k_zero_core.core.config import VECTOR_STORE_DIR

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Almacén vectorial persistente basado en ChromaDB.

    Cada documento indexado vive en su propia colección identificada por un hash
    único del contenido del archivo. Esto permite que múltiples documentos coexistan
    y que el mismo documento no sea re-indexado si ya existe.
    """

    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))

    def collection_exists(self, collection_id: str) -> bool:
        """
        Verifica si ya existe una colección con datos para este ID.

        Args:
            collection_id: Identificador único de la colección (hash del archivo).

        Returns:
            True si la colección existe y tiene al menos un chunk almacenado.
        """
        try:
            col = self._client.get_collection(name=collection_id)
            return col.count() > 0
        except Exception as exc:
            logger.debug("Colección ChromaDB '%s' no disponible: %s", collection_id, exc)
            return False

    def store(
        self,
        collection_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        """
        Guarda los chunks y sus embeddings en una colección ChromaDB.
        Usa upsert para idempotencia (si ya existe la colección, actualiza).

        Args:
            collection_id: Nombre de la colección (hash del archivo).
            chunks: Lista de fragmentos de texto del documento.
            embeddings: Vectores de embedding correspondientes a cada chunk.
        """
        collection = self._client.get_or_create_collection(
            name=collection_id,
            metadata={"hnsw:space": "cosine"},  # distancia coseno para similitud semántica
            embedding_function=None,             # usamos embeddings pre-computados de Ollama
        )
        ids = [f"chunk-{i}" for i in range(len(chunks))]
        collection.upsert(ids=ids, documents=chunks, embeddings=embeddings)

    def search(
        self,
        collection_id: str,
        query_embedding: list[float],
        top_k: int = 3,
    ) -> list[str]:
        """
        Busca los chunks más relevantes para el embedding de consulta.

        Args:
            collection_id: Colección donde buscar.
            query_embedding: Vector de la consulta del usuario.
            top_k: Número máximo de resultados a retornar.

        Returns:
            Lista de textos de los chunks más relevantes, ordenados por relevancia.
        """
        try:
            collection = self._client.get_collection(name=collection_id)
            n = min(top_k, collection.count())
            if n == 0:
                return []
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n,
                include=["documents"],
            )
            return results["documents"][0] if results["documents"] else []
        except Exception as exc:
            logger.warning("Error buscando en colección ChromaDB '%s': %s", collection_id, exc)
            return []

    def delete_collection(self, collection_id: str) -> None:
        """
        Elimina una colección y todos sus datos del vector store.

        Args:
            collection_id: ID de la colección a eliminar.
        """
        try:
            self._client.delete_collection(name=collection_id)
        except Exception as exc:
            logger.debug("No se pudo eliminar colección ChromaDB '%s': %s", collection_id, exc)

    def cleanup_orphan_collections(self, active_ids: set[str]) -> int:
        """
        Busca y elimina todas las colecciones cuyos IDs no estén en active_ids.
        Útil para el Garbage Collection de la CLI.
        
        Args:
            active_ids: Set de IDs de colecciones que deben conservarse.
            
        Returns:
            Número de colecciones eliminadas.
        """
        deleted_count = 0
        try:
            collections = self._client.list_collections()
            for col in collections:
                # El objeto devuelto por list_collections tiene un atributo .name
                col_name = getattr(col, "name", col) if not isinstance(col, str) else col
                if col_name not in active_ids:
                    self._client.delete_collection(name=col_name)
                    deleted_count += 1
        except Exception as e:
            logger.warning("Error limpiando colecciones en ChromaDB: %s", e)
        return deleted_count
