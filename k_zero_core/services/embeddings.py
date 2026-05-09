"""Clientes de embeddings usados por servicios RAG."""
from __future__ import annotations

from typing import Protocol

import ollama

from k_zero_core.core.exceptions import OllamaConnectionError


class EmbeddingClient(Protocol):
    """Contrato mínimo para generar embeddings de documentos y consultas."""

    def embed_documents(self, model: str, texts: list[str]) -> list[list[float]]:
        """Genera embeddings para una lista de textos."""
        ...

    def embed_query(self, model: str, text: str) -> list[float]:
        """Genera embedding para una consulta."""
        ...


class OllamaEmbeddingClient:
    """Implementación de embeddings usando Ollama local."""

    def embed_documents(self, model: str, texts: list[str]) -> list[list[float]]:
        try:
            response = ollama.embed(model=model, input=texts)
            return response.embeddings
        except Exception as e:
            raise OllamaConnectionError(f"Error generando embeddings: {e}") from e

    def embed_query(self, model: str, text: str) -> list[float]:
        try:
            response = ollama.embed(model=model, input=text)
            return response.embeddings[0]
        except Exception as e:
            raise OllamaConnectionError(f"Error al embeber la consulta: {e}") from e
