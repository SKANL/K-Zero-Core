"""
Motor de RAG semántico: chunking de texto, generación de embeddings via Ollama,
y búsqueda semántica a través del VectorStore.

Flujo de uso:
    engine = RagEngine(embedding_model, vector_store)
    engine.ingest(text, collection_id)    # primera vez
    chunks = engine.search(query, collection_id)  # por cada pregunta
"""
import logging

from k_zero_core.services.embeddings import EmbeddingClient, OllamaEmbeddingClient
from k_zero_core.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


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
    EMBEDDING_BATCH_SIZE = 50

    def __init__(
        self,
        embedding_model: str,
        vector_store: VectorStore,
        embedding_client: EmbeddingClient | None = None,
    ) -> None:
        """
        Args:
            embedding_model: Nombre del modelo de embedding en Ollama
                             (ej. 'nomic-embed-text-v2-moe:latest').
            vector_store: Instancia del VectorStore donde persistir los embeddings.
            embedding_client: Cliente para generar embeddings. Por defecto usa Ollama.
        """
        self.embedding_model = embedding_model
        self._store = vector_store
        self._embedding_client = embedding_client or OllamaEmbeddingClient()

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
        logger.info("Fragmentando en %s bloques...", total)

        # Prefijo "search_document: " recomendado por nomic para documentos indexados
        prefixed = [f"{self.DOC_PREFIX}{chunk}" for chunk in chunks]

        logger.info("Generando embeddings con '%s'...", self.embedding_model)
        embeddings = [
            embedding
            for i in range(0, len(prefixed), self.EMBEDDING_BATCH_SIZE)
            for embedding in self._embedding_client.embed_documents(
                self.embedding_model,
                prefixed[i:i + self.EMBEDDING_BATCH_SIZE],
            )
        ]

        logger.info("Guardando en base de datos vectorial...")
        self._store.store(collection_id, chunks, embeddings)
        return total

    def search(self, query: str, collection_id: str, top_k: int = 3) -> list[str]:
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
        query_embedding = self._embedding_client.embed_query(
            self.embedding_model,
            f"{self.QUERY_PREFIX}{query}",
        )

        return self._store.search(collection_id, query_embedding, top_k)

    def _chunk_text(self, text: str) -> list[str]:
        """
        Divide el texto en bloques de aproximadamente CHUNK_SIZE palabras con CHUNK_OVERLAP de solapamiento.
        Respeta límites de oraciones (puntuación) para no romper el sentido semántico.

        Args:
            text: Texto completo a dividir.

        Returns:
            Lista de bloques de texto.
        """
        import re
        
        # Dividir por signos de puntuación finales (., \n\n, ?, !) manteniendo delimitadores
        sentences_raw = re.split(r'(?<=[.?!])\s+|\n\n+', text)
        sentences = [s.strip() for s in sentences_raw if s.strip()]
        
        chunks = []
        current_chunk = []
        current_words = 0
        
        for sentence in sentences:
            words = sentence.split()
            word_count = len(words)
            
            if current_words + word_count > self.CHUNK_SIZE and current_chunk:
                chunks.append(" ".join(current_chunk))
                # Mantener oraciones finales para solapamiento
                overlap_chunk = []
                overlap_words = 0
                for s in reversed(current_chunk):
                    s_words = len(s.split())
                    if overlap_words + s_words <= self.CHUNK_OVERLAP:
                        overlap_chunk.insert(0, s)
                        overlap_words += s_words
                    else:
                        break
                current_chunk = overlap_chunk
                current_words = overlap_words
                
            current_chunk.append(sentence)
            current_words += word_count
            
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks
