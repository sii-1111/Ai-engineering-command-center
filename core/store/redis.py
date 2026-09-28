"""Small Redis-backed task/event store used by the API layer.

The store is intentionally optional: local development can run without Redis,
while production deployments can enable it through REDIS_URL.
"""

import json
import os
from typing import Any

import redis


def _client():
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    return redis.Redis.from_url(url, decode_responses=True)


def save_task_snapshot(task_id: str, state: dict[str, Any]) -> bool:
    client = _client()
    if client is None:
        return False
    client.set(f"task:{task_id}", json.dumps(state, default=str))
    return True


def get_task_snapshot(task_id: str) -> dict[str, Any] | None:
    client = _client()
    if client is None:
        return None
    value = client.get(f"task:{task_id}")
    return json.loads(value) if value else None


def healthcheck() -> bool:
    client = _client()
    return bool(client and client.ping())
