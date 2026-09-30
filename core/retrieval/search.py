"""Local repository-aware retrieval service."""

import json
import os
from pathlib import Path

from core.retrieval.local_search import LocalRepositoryRetriever, LocalSearchConfig


def search_repository(
    query: str,
    *,
    repository: str,
    ref: str = "main",
    top_k: int = 5,
    retriever: LocalRepositoryRetriever | None = None,
    embedding_provider: object | None = None,
) -> list[dict[str, object]]:
    """Run repository-scoped local retrieval over an optional JSONL index."""
    if not query.strip() or top_k <= 0:
        return []

    if retriever is None:
        try:
            retriever = LocalRepositoryRetriever(LocalSearchConfig.from_environment())
        except ValueError:
            return []

    documents = retriever.search(query, repository=repository, ref=ref, top_k=top_k)
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
