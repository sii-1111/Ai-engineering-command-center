"""Repository ingestion primitives for Blob Storage and deterministic chunking.

The ingestion layer is intentionally provider-oriented: storage discovery and
chunking are separate from indexing so the same pipeline can be tested locally
and later connected to Azure Blob Storage without changing retrieval behavior.
"""

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol


@dataclass(frozen=True)
class RepositoryFile:
    path: str
    content: str
    commit_sha: str
    repository: str
    ref: str


@dataclass(frozen=True)
class RepositoryChunk:
    id: str
    source: str
    content: str
    repository: str
    ref: str
    commit_sha: str
    chunk_index: int


class RepositorySource(Protocol):
    def list_files(self, repository: str, ref: str) -> list[RepositoryFile]:
        """Return text files available for indexing."""


def chunk_repository_file(
    file: RepositoryFile,
    *,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[RepositoryChunk]:
    """Split a repository file into stable, overlapping character chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")
    if not file.content:
        return []

    step = chunk_size - overlap
    chunks: list[RepositoryChunk] = []
    for index, start in enumerate(range(0, len(file.content), step)):
        content = file.content[start : start + chunk_size]
        if not content:
            continue
        raw_id = f"{file.repository}:{file.ref}:{file.path}:{file.commit_sha}:{index}"
        chunk_id = sha256(raw_id.encode("utf-8")).hexdigest()
        chunks.append(
            RepositoryChunk(
                id=chunk_id,
                source=file.path,
                content=content,
                repository=file.repository,
                ref=file.ref,
                commit_sha=file.commit_sha,
                chunk_index=index,
            )
        )
        if start + chunk_size >= len(file.content):
            break
    return chunks
