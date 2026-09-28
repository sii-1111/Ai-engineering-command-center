from core.retrieval.repository import RepositoryRetriever, RetrievalDocument


def test_repository_retriever_ranks_matching_evidence() -> None:
    retriever = RepositoryRetriever(
        [
            RetrievalDocument("a.py", "search endpoint database query"),
            RetrievalDocument("b.py", "health endpoint response"),
        ]
    )
    results = retriever.search("search database", top_k=1)
    assert len(results) == 1
    assert results[0].source == "a.py"


def test_repository_retriever_handles_empty_queries() -> None:
    retriever = RepositoryRetriever()
    assert retriever.search("", top_k=5) == []
    assert retriever.search("anything", top_k=0) == []
