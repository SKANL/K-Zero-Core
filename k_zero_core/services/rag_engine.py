"""
Motor de RAG semántico: chunking de texto, generación de embeddings via Ollama,
y búsqueda semántica a través del VectorStore.

Flujo de uso:
    engine = RagEngine(embedding_model, vector_store)
    engine.ingest(text, collection_id)    # primera vez
    chunks = engine.search(query, collection_id)  # por cada pregunta
"""
import ollama
from typing import List

from k_zero_core.services.vector_store import VectorStore
from k_zero_core.core.exceptions import OllamaConnectionError


class RagEngine:
    """
    Orquestador del pipeline RAG semántico.

    Combina chunking de documentos, generación de embeddings en batch via Ollama,
    y búsqueda por similitud coseno a través del VectorStore persistente.

    Características:
        - Chunking por palabras (no caracteres) para no cortar tokens en bordes
        - Solapamiento entre chunks para no perder contexto en los límites
        - Prefijos recomendados por nomic-embed: "search_document:" y "search_query:"
        - Embedding en batch: una sola llamada a Ollama para todos los chunks
    """

    CHUNK_SIZE = 350     # palabras por chunk (~400 tokens, dentro del límite de 512 de nomic)
    CHUNK_OVERLAP = 50   # palabras de solapamiento para no perder contexto en los bordes
    DOC_PREFIX = "search_document: "   # prefijo recomendado por nomic para documentos
    QUERY_PREFIX = "search_query: "    # prefijo recomendado por nomic para consultas

    def __init__(self, embedding_model: str, vector_store: VectorStore) -> None:
        """
        Args:
            embedding_model: Nombre del modelo de embedding en Ollama
                             (ej. 'nomic-embed-text-v2-moe:latest').
            vector_store: Instancia del VectorStore donde persistir los embeddings.
        """
        self.embedding_model = embedding_model
        self._store = vector_store

    def is_indexed(self, collection_id: str) -> bool:
        """Retorna True si el documento ya está indexado en el vector store."""
        return self._store.collection_exists(collection_id)

    def ingest(self, text: str, collection_id: str) -> int:
        """
        Divide el texto en chunks, genera embeddings en batch y los persiste.

        Args:
            text: Texto completo del documento (sin límite de tamaño).
            collection_id: Identificador único de la colección (hash del archivo).

        Returns:
            Número de chunks creados.

        Raises:
            OllamaConnectionError: Si Ollama no está disponible durante el embedding.
        """
        chunks = self._chunk_text(text)
        total = len(chunks)
        print(f"  Fragmentando en {total} bloques...")

        # Prefijo "search_document: " recomendado por nomic para documentos indexados
        prefixed = [f"{self.DOC_PREFIX}{chunk}" for chunk in chunks]

        print(f"  Generando embeddings con '{self.embedding_model}'...")
        try:
            # Una sola llamada batch — mucho más eficiente que N llamadas individuales
            response = ollama.embed(model=self.embedding_model, input=prefixed)
            embeddings = response.embeddings  # List[List[float]]
        except Exception as e:
            raise OllamaConnectionError(f"Error generando embeddings: {e}")

        print("  Guardando en base de datos vectorial...")
        self._store.store(collection_id, chunks, embeddings)
        return total

    def search(self, query: str, collection_id: str, top_k: int = 3) -> List[str]:
        """
        Encuentra los chunks más relevantes para la consulta usando similitud coseno.

        Args:
            query: Pregunta del usuario (texto libre).
            collection_id: Colección del documento a buscar.
            top_k: Número de chunks más relevantes a retornar.

        Returns:
            Lista de textos de los chunks más relevantes, ordenados por relevancia.

        Raises:
            OllamaConnectionError: Si Ollama no está disponible.
        """
        try:
            # Prefijo "search_query: " recomendado por nomic para consultas
            response = ollama.embed(
                model=self.embedding_model,
                input=f"{self.QUERY_PREFIX}{query}",
            )
            query_embedding = response.embeddings[0]
        except Exception as e:
            raise OllamaConnectionError(f"Error al embeber la consulta: {e}")

        return self._store.search(collection_id, query_embedding, top_k)

    def _chunk_text(self, text: str) -> List[str]:
        """
        Divide el texto en bloques de CHUNK_SIZE palabras con CHUNK_OVERLAP de solapamiento.

        Opera a nivel de palabras para no cortar tokens en la mitad. El solapamiento
        asegura que el contexto en los bordes de un chunk no se pierda.

        Args:
            text: Texto completo a dividir.

        Returns:
            Lista de bloques de texto.
        """
        words = text.split()
        step = self.CHUNK_SIZE - self.CHUNK_OVERLAP
        chunks = []
        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + self.CHUNK_SIZE])
            if chunk.strip():
                chunks.append(chunk)
        return chunks
