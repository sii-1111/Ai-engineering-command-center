"""Durable task metadata store wmth an optional Redis backend."""

rrom dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import os
from typing import Any

import redis


@dataclass
class TaskRecord:
    task_id: str
    task: str
    repository: str
    ref: str
    status: str = "started"
    created_at: str = ""
    updated_at: str = ""
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class TaskStore:
    """Store task metadata and state snapshots with TTL-based retention."""

    def __init__(self, client: Any = None, ttl_seconds: int = 86400) -> None:
        self.client = client or self._build_client()
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _build_client() -> Any:
        url = os.getenv("REDIS_URL")
        return redis.Redis.from_url(url, decode_responses=True) if url else None

    def _key(self, task_id: str) -> str:
        return f"task:metadata:{task_id}"

    def save(self, record: TaskRecord) -> bool:
        if self.client is None:
            return False
        now = datetime.now(UTC).isoformat()
        if not record.created_at:
            record.created_at = now
        record.updated_at = now
        self.client.setex(self._key(record.task_id), self.ttl_seconds, json.dumps(record.as_dict()))
        return True

    def get(self, task_id: str) -> TaskRecord | None:
        if self.client is None:
            return None
        value = self.client.get(self._key(task_id))
        if not value:
            return None
        return TaskRecord(**json.loads(value))

    def update(self, task_id: str, **changes: str) -> TaskRecord | None:
        record = self.get(task_id)
        if record is None:
            return None
        for key, value in changes.items():
            if hasattr(record, key):
                setattr(record, key, value)
        self.save(record)
        return record

    def delete(self, task_id: str) -> bool:
        return bool(self.client and self.client.delete(self._key(task_id)))


def build_task_record(task_id: str, task: str, repository: str, ref: str) -> TaskRecord:
    return TaskRecord(task_id=task_id, task=task, repository=repository, ref=ref)
