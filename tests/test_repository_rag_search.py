from unittest.mock import Mock

from core.retrieval.local_search import LocalRepositoryRetriever
from core.retrieval.search import search_repository


def test_search_repository_scopes_results_to_repository_and_ref() -> None:
    retriever = Mock(spec=LocalRepositoryRetriever)
    retriever.search.return_value = [
        Mock(source="apps/api/app/main.py", content="slow query", score=4.2)
    ]

    results = search_repository(
        "slow query",
        repository="owner/repo",
        ref="main",
        top_k=3,
        retriever=retriever,
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
        repository="owner/repo",
        ref="main",
        top_k=3,
    )


def test_search_repository_returns_empty_without_local_index(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_RETRIEVAL_INDEX", str(tmp_path / "missing.jsonl"))
    assert search_repository("find a function", repository="owner/repo") == []
