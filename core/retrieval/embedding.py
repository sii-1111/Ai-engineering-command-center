"""Gemini embedding provider boundary for repository indexing."""

from collections.abc import Sequence
from typing import Protocol


class EmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector for each input text."""


class GeminiEmbeddingProvider:
    """Gemini embeddings adapter using the OpenAI-compatible API."""

    def __init__(self, client: object, model: str = "gemini-embedding-001") -> None:
        self.client = client
        self.model = model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.model, input=list(texts))
        return [list(item.embedding) for item in response.data]
