"""Azure AI Search adapter for repository retrieval.

The adapter keeps Azure-specific SDK code behind the repository retrieval
contract. It supports hybrid keyword + vector search when a vector query is
provided, while remaining usable with keyword search alone.
"""

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
    """Retrieve repository chunks from an Azure AI Search index."""

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

        results = self.client.search(
            search_text=query,
            vector_queries=vector_queries,
            top=top_k,
            select=["source", "content"],
        )
        return [
            RetrievalDocument(
                source=str(item.get("source", "unknown")),
                content=str(item.get("content", "")),
                score=float(item.get("@search.score", 0.0)),
            )
            for item in results
        ]
