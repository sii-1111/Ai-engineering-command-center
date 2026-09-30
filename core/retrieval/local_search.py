"""Local JSONL repository retrieval with lightweight lexical ranking."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from core.retrieval.repository import RetrievalDocument


@dataclass(frozen=True)
class LocalSearchConfig:
    index_path: str = ".data/repository-index.jsonl"

    @classmethod
    def from_environment(cls) -> "LocalSearchConfig":
        return cls(os.getenv("LOCAL_RETRIEVAL_INDEX", ".data/repository-index.jsonl"))


class LocalRepositoryRetriever:
    """Retrieve repository chunks from a local JSONL index without cloud services."""

    def __init__(self, config: LocalSearchConfig) -> None:
        self.index_path = Path(config.index_path)

    def _documents(self) -> list[dict[str, object]]:
        if not self.index_path.exists():
            return []
        documents = []
        for line in self.index_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("content"):
                documents.append(item)
        return documents

    def search(self, query: str, *, repository: str | None = None, ref: str | None = None, top_k: int = 5) -> list[RetrievalDocument]:
        if top_k <= 0 or not query.strip():
            return []
        terms = {term.lower() for term in query.split() if term.strip()}
        ranked = []
        for item in self._documents():
            if repository and item.get("repository") != repository:
                continue
            if ref and item.get("ref") != ref:
                continue
            content = str(item.get("content", ""))
            overlap = len(terms & set(content.lower().split()))
            score = float(item.get("score", 0.0) or 0.0) + overlap / max(len(terms), 1)
            if score > 0:
                ranked.append((score, RetrievalDocument(str(item.get("source", "unknown")), content, score)))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [document for _, document in ranked[:top_k]]
