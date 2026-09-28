import pytest

from core.retrieval.ingestion import RepositoryFile, chunk_repository_file


def test_chunking_preserves_repository_metadata_and_is_stable() -> None:
    file = RepositoryFile(
        path="apps/api/app/main.py",
        content="abcdefghij",
        commit_sha="abc123",
        repository="owner/repo",
        ref="main",
    )

    chunks = chunk_repository_file(file, chunk_size=6, overlap=2)

    assert [chunk.content for chunk in chunks] == ["abcdef", "efghij"]
    assert all(chunk.source == file.path for chunk in chunks)
    assert all(chunk.repository == "owner/repo" for chunk in chunks)
    assert chunks[0].id == chunk_repository_file(file, chunk_size=6, overlap=2)[0].id


def test_chunking_handles_empty_files() -> None:
    file = RepositoryFile("empty.py", "", "sha", "owner/repo", "main")
    assert chunk_repository_file(file) == []


@pytest.mark.parametrize(
    "chunk_size,overlap",
    [(0, 0), (10, 10), (10, 11), (10, -1)],
)
def test_chunking_validates_configuration(chunk_size: int, overlap: int) -> None:
    file = RepositoryFile("a.py", "content", "sha", "owner/repo", "main")
    with pytest.raises(ValueError):
        chunk_repository_file(file, chunk_size=chunk_size, overlap=overlap)
