"""Repository-aware RAG query service."""

import os
from typing import Any

from openai import AzureOpenAI

from core.retrieval.azure_search import AzureRepositoryRetriever, AzureSearchConfig
from core.retrieval.embedding import AzureOpenAIEmbeddingProvider


def search_repository(
    query: str,
    *,
    repository: str,
    ref: str = "main",
    top_k: int = 5,
    retriever: AzureRepositoryRetriever | None = None,
    embedding_provider: Any | None = None,
) -> list[dict[str, object]]:
    """Run repository-scoped hybrid retrieval and return evidence records."""
    if not query.strip() or top_k <= 0:
        return []

    if retriever is None:
        try:
            retriever = AzureRepositoryRetriever(AzureSearchConfig.from_environment())
        except ValueError:
            return []
    if embedding_provider is None:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "")
        if endpoint and api_key and deployment:
            embedding_provider = AzureOpenAIEmbeddingProvider(
                AzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
                ),
                deployment,
            )

    embedding = embedding_provider.embed([query])[0] if embedding_provider else None
    documents = retriever.search(
        query,
        embedding=embedding,
        repository=repository,
        ref=ref,
        top_k=top_k,
    )
    return [
        {
            "source": document.source,
            "content": document.content,
            "score": document.score,
            "repository": repository,
            "ref": ref,
        }
        for document in documents
    ]
