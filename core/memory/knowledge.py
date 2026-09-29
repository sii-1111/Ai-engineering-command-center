"""Long-term engineering knowledge storage and retrieval.

Knowledge is promoted only after verification/review and is stored as a
portable record. PostgreSQL is used when configured; an in-memory backend keeps
local development and tests deterministic.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
import os
from threading import Lock
from typing import Any, Protocol


@dataclass(frozen=True)
class EngineeringKnowledge:
    knowledge_id: str
    task_id: str
    repository: str
    ref: str
    root_cause: str
    fix: str
    files: tuple[str, ...] = ()
    verification: str = ""
    confidence: float = 0.0
    pull_request: str = ""
    tags: tuple[str, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "task_id": self.task_id,
            "repository": self.repository,
            "ref": self.ref,
            "root_cause": self.root_cause,
            "fix": self.fix,
            "files": list(self.files),
            "verification": self.verification,
            "confidence": self.confidence,
            "pull_request": self.pull_request,
            "tags": list(self.tags),
            "created_at": self.created_at,
        }


class KnowledgeStore(Protocol):
    def save(self, knowledge: EngineeringKnowledge) -> None: ...
    def search(self, query: str, repository: str | None = None, top_k: int = 5) -> list[EngineeringKnowledge]: ...


class InMemoryKnowledgeStore:
    def __init__(self) -> None:
        self._items: list[EngineeringKnowledge] = []
        self._lock = Lock()

    def save(self, knowledge: EngineeringKnowledge) -> None:
        with self._lock:
            self._items.append(knowledge)

    def search(self, query: str, repository: str | None = None, top_k: int = 5) -> list[EngineeringKnowledge]:
        if top_k <= 0 or not query.strip():
            return []
        terms = set(query.lower().split())
        scored = []
        with self._lock:
            for item in self._items:
                if repository and item.repository != repository:
                    continue
                text = " ".join([item.root_cause, item.fix, *item.files, *item.tags]).lower()
                overlap = len(terms & set(text.split()))
                if overlap:
                    scored.append((overlap, item))
        scored.sort(key=lambda value: value[0], reverse=True)
        return [item for _, item in scored[:top_k]]


def knowledge_from_state(state: dict[str, Any]) -> EngineeringKnowledge | None:
    report = state.get("report", {})
    verification = state.get("verification_result", {})
    review = state.get("review", {})
    if (
        not report.get("root_cause")
        or not report.get("recommended_change")
        or state.get("verification_status") != "passed"
        or review.get("decision") != "approve"
    ):
        return None

    task_id = str(state.get("task_id", state.get("task", "unknown")))
    pr = state.get("pull_request", {})
    return EngineeringKnowledge(
        knowledge_id=f"{state.get('repository', 'repo')}:{task_id}",
        task_id=task_id,
        repository=str(state.get("repository", "")),
        ref=str(state.get("ref", "main")),
        root_cause=str(report["root_cause"]),
        fix=str(report["recommended_change"]),
        files=tuple(report.get("files_involved", [])),
        verification=str(verification),
        confidence=float(review.get("confidence", report.get("confidence", 0.0))),
        pull_request=str(pr.get("url", pr.get("number", ""))),
        tags=tuple(_tags(state)),
    )


def _tags(state: dict[str, Any]) -> list[str]:
    report = state.get("report", {})
    return [
        str(tag)
        for tag in {
            str(report.get("root_cause", "")).split()[0] if report.get("root_cause") else "",
            str(state.get("repository", "")),
        }
        if tag
    ]


def get_knowledge_store() -> KnowledgeStore:
    if os.getenv("DATABASE_URL"):
        try:
            from core.memory.knowledge_store import PostgresKnowledgeStore
            store = PostgresKnowledgeStore(os.environ["DATABASE_URL"])
            store.setup()
            return store
        except (ImportError, OSError):
            pass
    return _DEFAULT_STORE


_DEFAULT_STORE = InMemoryKnowledgeStore()
