from unittest.mock import MagicMock, patch

import pytest

from core.retrieval.azure_search import AzureRepositoryRetriever, AzureSearchConfig


def test_config_requires_azure_search_credentials(monkeypatch):
    monkeypatch.delenv("AZURE_SEARCH_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_SEARCH_API_KEY", raising=False)
    with pytest.raises(ValueError, match="AZURE_SEARCH_ENDPOINT"):
        AzureSearchConfig.from_environment()


@patch("core.retrieval.azure_search.SearchClient")
def test_azure_retriever_supports_keyword_search(search_client):
    search_client.return_value.search.return_value = [
        {"source": "app.py", "content": "search handler", "@search.score": 2.5}
    ]
    retriever = AzureRepositoryRetriever(
        AzureSearchConfig("https://example.search.windows.net", "repo", "key")
    )
    results = retriever.search("search handler", top_k=1)
    assert results[0].source == "app.py"
    assert results[0].score == 2.5
    search_client.return_value.search.assert_called_once()


@patch("core.retrieval.azure_search.SearchClient")
def test_azure_retriever_returns_empty_for_invalid_query(search_client):
    retriever = AzureRepositoryRetriever(
        AzureSearchConfig("https://example.search.windows.net", "repo", "key")
    )
    assert retriever.search("", top_k=5) == []
    search_client.return_value.search.assert_not_called()
