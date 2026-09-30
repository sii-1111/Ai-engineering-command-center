"""Local filesystem source for repository text ingestion."""

import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from core.retrieval.ingestion import RepositoryFile

_SUPPORTED_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml", ".md", ".txt")


@dataclass(frozen=True)
class LocalRepositorySourceConfig:
    root: str = ".data/repositories"

    @classmethod
    def from_environment(cls) -> "LocalRepositorySourceConfig":
        return cls(os.getenv("LOCAL_REPOSITORY_ROOT", ".data/repositories"))


class LocalRepositorySource:
    """Read repository files from owner/repository/ref directories."""

    def __init__(self, config: LocalRepositorySourceConfig) -> None:
        self.root = Path(config.root)

    def list_files(self, repository: str, ref: str) -> list[RepositoryFile]:
        repository_root = self.root / repository / ref
        if not repository_root.exists():
            return []
        files = []
        for path in repository_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in _SUPPORTED_SUFFIXES:
                continue
            content = path.read_text(encoding="utf-8")
            files.append(RepositoryFile(
                path=path.relative_to(repository_root).as_posix(),
                content=content,
                commit_sha=sha256(content.encode("utf-8")).hexdigest(),
                repository=repository,
                ref=ref,
            ))
        return files
