from core.retrieval.indexing import build_search_documents
from core.retrieval.ingestion import RepositoryFile, chunk_repository_file


class FakeEmbeddingProvider:
    def __init__(self, vectors):
        self.vectors = vectors
        self.inputs = []

    def embed(self, texts):
        self.inputs.append(list(texts))
        return self.vectors


def test_build_search_documents_preserves_metadata_and_vectors():
    chunks = chunk_repository_file(
        RepositoryFile("app.py", "search latency", "sha", "owner/repo", "main"),
        chunk_size=100,
        overlap=0,
    )
    provider = FakeEmbeddingProvider([[0.1, 0.2]])

    documents = build_search_documents(chunks, embedding_provider=provider)

    assert documents[0]["source"] == "app.py"
    assert documents[0]["repository"] == "owner/repo"
    assert documents[0]["commit_sha"] == "sha"
    assert documents[0]["contentVector"] == [0.1, 0.2]
    assert provider.inputs == [["search latency"]]


def test_build_search_documents_rejects_vector_count_mismatch():
    chunks = chunk_repository_file(
        RepositoryFile("app.py", "abcdef", "sha", "owner/repo", "main"),
        chunk_size=3,
        overlap=0,
    )
    provider = FakeEmbeddingProvider([[0.1]])

    try:
        build_search_documents(chunks, embedding_provider=provider)
    except ValueError as exc:
        assert "unexpected number" in str(exc)
    else:
        raise AssertionError("expected ValueError")
