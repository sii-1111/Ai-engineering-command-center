"""Azure AI Search adapter for repository retrieval."""

import os
from collections.abc import Sequence
from dataclasses import dataclass

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

from core.retrieval.repository import RetrievalDocument


@dataclass(frozen=True)
class AzureSearchConfig:
    endpoint: str
    index_name: str
    api_key: str

    @classmethod
    def from_environment(cls) -> "AzureSearchConfig":
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
        index_name = os.getenv("AZURE_SEARCH_INDEX", "repository-docs")
        api_key = os.getenv("AZURE_SEARCH_API_KEY", "")
        if not endpoint or not api_key:
            raise ValueError("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY are required")
        return cls(endpoint, index_name, api_key)


class AzureRepositoryRetriever:
    """Retrieve repository chunks from Azure AI Search with keyword/vector search."""

    def __init__(self, config: AzureSearchConfig) -> None:
        self.client = SearchClient(
            endpoint=config.endpoint,
            index_name=config.index_name,
            credential=AzureKeyCredential(config.api_key),
        )

    def search(
        self,
        query: str,
        *,
        embedding: Sequence[float] | None = None,
        repository: str | None = None,
        ref: str | None = None,
        top_k: int = 5,
    ) -> list[RetrievalDocument]:
        if top_k <= 0 or not query.strip():
            return []

        vector_queries = None
        if embedding:
            vector_queries = [
                VectorizedQuery(
                    vector=list(embedding),
                    k_nearest_neighbors=top_k,
                    fields="contentVector",
                )
            ]

        filters = []
        if repository:
            filters.append(f"repository eq '{repository.replace(chr(39), chr(39) * 2)}'")
        if ref:
            filters.append(f"ref eq '{ref.replace(chr(39), chr(39) * 2)}'")

        results = self.client.search(
            search_text=query,
            vector_queries=vector_queries,
            filter=" and ".join(filters) if filters else None,
            top=top_k,
            select=["source", "content", "repository", "ref", "commit_sha", "chunk_index"],
        )
        return [
            RetrievalDocument(
                source=str(item.get("source", "unknown")),
                content=str(item.get("content", "")),
                score=float(item.get("@search.score", 0.0)),
            )
            for item in results
        ]
