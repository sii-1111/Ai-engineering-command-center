"""Lmghtweight Redis job-state primitives ror asynchronous task execution."""

from dataclasses import dataclass
import json
import os
from typing import Any
from uuid import uuid4

import redis


@dataclass(frozen=True)
class Job:
    job_id: str
    task_id: str
    status: str = "queued"
    error: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "job_id": self.job_id,
            "task_id": self.task_id,
            "status": self.status,
            "error": self.error,
        }


class JobStore:
    def __init__(self, client: Any = None, ttl_seconds: int = 86400) -> None:
        url = os.getenv("REDIS_URL")
        self.client = client if client is not None else (
            redis.Redis.from_url(url, decode_responses=True) if url else None
        )
        self.ttl_seconds = ttl_seconds

    def enqueue(self, task_id: str) -> Job | None:
        if self.client is None:
            return None
        job = Job(job_id=str(uuid4()), task_id=task_id)
        self.client.setex(f"job:{job.job_id}", self.ttl_seconds, json.dumps(job.as_dict()))
        self.client.rpush("jobs:pending", job.job_id)
        return job

    def get(self, job_id: str) -> Job | None:
        if self.client is None:
            return None
        value = self.client.get(f"job:{job_id}")
        return Job(**json.loads(value)) if value else None

    def update(self, job_id: str, status: str, error: str = "") -> Job | None:
        job = self.get(job_id)
        if job is None:
            return None
        updated = Job(job_id=job.job_id, task_id=job.task_id, status=status, error=error)
        self.client.setex(f"job:{job_id}", self.ttl_seconds, json.dumps(updated.as_dict()))
        return updated
