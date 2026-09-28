"""Embedding provider boundary for repository indexing."""

from collections.abc import Sequence
from typing import Protocol


class EmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector for each input text."""


class AzureOpenAIEmbeddingProvider:
    """Azure OpenAI embeddings adapter using the configured deployment."""

    def __init__(self, client: object, deployment: str) -> None:
        self.client = client
        self.deployment = deployment

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.deployment, input=list(texts))
        return [list(item.embedding) for item in response.data]
