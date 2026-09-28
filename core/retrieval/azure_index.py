"""Azure AI Search indexing adapter for repository chunks."""

from dataclasses import dataclass

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


@dataclass(frozen=True)
class AzureSearchIndexer:
    """Upload prepared repository documents into an Azure AI Search index."""

    client: SearchClient

    @classmethod
    def from_config(cls, endpoint: str, index_name: str, api_key: str) -> "AzureSearchIndexer":
        if not endpoint or not index_name or not api_key:
            raise ValueError("endpoint, index_name and api_key are required")
        return cls(
            SearchClient(endpoint, index_name, AzureKeyCredential(api_key))
        )

    def upsert(self, documents: list[dict]) -> int:
        """Merge-or-upload documents and return the number submitted."""
        if not documents:
            return 0
        result = self.client.merge_or_upload_documents(documents=documents)
        return len(result)
