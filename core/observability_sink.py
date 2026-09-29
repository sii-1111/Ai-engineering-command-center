"""Optional Redis sink for durable observability events."""

import json
import os
from typing import Any

import redis


class ObservabilitySink:
    def __init__(self, client: Any = None, ttl_seconds: int = 604800) -> None:
        url = os.getenv("REDIS_URL")
        self.client = client if client is not None else (
            redis.Redis.from_url(url, decode_responses=True) if url else None
        )
        self.ttl_seconds = ttl_seconds

    def write(self, task_id: str, events: list[dict[str, Any]]) -> bool:
        if self.client is None:
            return False
        self.client.setex(f"observability:{task_id}", self.ttl_seconds, json.dumps(events))
        return True

    def read(self, task_id: str) -> list[dict[str, Any]]:
        if self.client is None:
            return []
        value = self.client.get(f"observability:{task_id}")
        return json.loads(value) if value else []
