from unittest.mock import Mock, patch

from core.retrieval.azure_search import AzureRepositoryRetriever, AzureSearchConfig
from core.retrieval.search import search_repository


@patch("core.retrieval.search.AzureRepositoryRetriever")
def test_search_repository_scopes_results_to_repository_and_ref(retriever_cls):
    retriever = Mock()
    retriever_cls.return_value = retriever
    retriever.search.return_value = [
        Mock(source="apps/api/app/main.py", content="slow query", score=4.2)
    ]

    results = search_repository(
        "slow query",
        repository="owner/repo",
        ref="main",
        top_k=3,
        retriever=retriever,
        embedding_provider=None,
    )

    assert results == [{
        "source": "apps/api/app/main.py",
        "content": "slow query",
        "score": 4.2,
        "repository": "owner/repo",
        "ref": "main",
    }]
    retriever.search.assert_called_once_with(
        "slow query",
        embedding=None,
        repository="owner/repo",
        ref="main",
        top_k=3,
    )


@patch("core.retrieval.search.AzureRepositoryRetriever")
def test_search_repository_skips_when_azure_search_is_not_configured(retriever_cls, monkeypatch):
    monkeypatch.delenv("AZURE_SEARCH_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_SEARCH_API_KEY", raising=False)

    assert search_repository("find a function", repository="owner/repo") == []
    retriever_cls.assert_not_called()


@patch("core.retrieval.azure_search.SearchClient")
def test_azure_retriever_passes_repository_and_ref_filter(search_client):
    search_client.return_value.search.return_value = []
    retriever = AzureRepositoryRetriever(
        AzureSearchConfig("https://example.search.windows.net", "repo", "key")
    )

    retriever.search("latency", repository="owner/repo", ref="main", top_k=5)

    kwargs = search_client.return_value.search.call_args.kwargs
    assert kwargs["filter"] == "repository eq 'owner/repo' and ref eq 'main'"
    assert "repository" in kwargs["select"]
    assert "ref" in kwargs["select"]
