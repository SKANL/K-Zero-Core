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
            BATCH_SIZE = 50
            all_embeddings = []
            # Dividir en lotes para no sobrecargar a Ollama (evita errores OOM en documentos grandes)
            for i in range(0, len(prefixed), BATCH_SIZE):
                batch = prefixed[i:i + BATCH_SIZE]
                response = ollama.embed(model=self.embedding_model, input=batch)
                all_embeddings.extend(response.embeddings)
            embeddings = all_embeddings  # List[List[float]]
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
