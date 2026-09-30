"""Provider-neutral conversion of repository chunks into search documents."""

from dataclasses import asdict
from typing import Any

from core.retrieval.embedding import EmbeddingProvider
from core.retrieval.ingestion import RepositoryChunk


def build_search_documents(
    chunks: list[RepositoryChunk],
    *,
    embedding_provider: EmbeddingProvider,
) -> list[dict[str, Any]]:
    """Create provider-neutral documents with content vectors."""
    if not chunks:
        return []
    vectors = embedding_provider.embed([chunk.content for chunk in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("embedding provider returned an unexpected number of vectors")
    documents: list[dict[str, Any]] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        document = asdict(chunk)
        document["contentVector"] = vector
        documents.append(document)
    return documents
