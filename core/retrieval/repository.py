"""Repository-aware retrieval primitives.

This module provides a provider-neutral retrieval interface and a deterministic
local implementation over evidence already collected by the investigation.
Azure AI Search can implement the same interface without changing agents.
"""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RetrievalDocument:
    source: str
    content: str
    score: float = 0.0


class RepositoryRetriever:
    """Retrieve repository evidence with lightweight lexical scoring."""

    def __init__(self, documents: Iterable[RetrievalDocument] = ()) -> None:
        self._documents = list(documents)

    def add(self, document: RetrievalDocument) -> None:
        self._documents.append(document)

    def search(self, query: str, top_k: int = 5) -> list[RetrievalDocument]:
        if top_k <= 0 or not query.strip():
            return []
        terms = {term.lower() for term in query.split() if term.strip()}
        ranked: list[tuple[float, RetrievalDocument]] = []
        for document in self._documents:
            tokens = set(document.content.lower().split())
            overlap = len(terms & tokens)
            score = document.score + overlap / max(len(terms), 1)
            if score > 0:
                ranked.append((score, document))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [document for _, document in ranked[:top_k]]
