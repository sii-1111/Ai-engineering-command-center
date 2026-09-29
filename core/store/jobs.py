"""Redis-backed job-state primitives for asynchronous task execution."""

import json
import os
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import redis


@dataclass(frozen=True)
class Job:
    job_id: str
    task_id: str
    status: str = "queued"
    error: str = ""
    attempts: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {"job_id": self.job_id, "task_id": self.task_id, "status": self.status, "error": self.error, "attempts": self.attempts}


class JobStore:
    def __init__(self, client: Any = None, ttl_seconds: int = 86400) -> None:
        url = os.getenv("REDIS_URL")
        self.client = client if client is not None else (redis.Redis.from_url(url, decode_responses=True) if url else None)
        self.ttl_seconds = ttl_seconds

    def enqueue(self, task_id: str) -> Job | None:
        if self.client is None:
            return None
        job = Job(job_id=str(uuid4()), task_id=task_id)
        self._save(job)
        self.client.rpush("jobs:pending", job.job_id)
        return job

    def get(self, job_id: str) -> Job | None:
        if self.client is None:
            return None
        value = self.client.get(f"job:{job_id}")
        return Job(**json.loads(value)) if value else None

    def update(self, job_id: str, status: str, error: str = "", attempts: int | None = None) -> Job | None:
        job = self.get(job_id)
        if job is None:
            return None
        updated = Job(job_id=job.job_id, task_id=job.task_id, status=status, error=error, attempts=job.attempts if attempts is None else attempts)
        self._save(updated)
        return updated

    def increment_attempts(self, job_id: str) -> Job | None:
        job = self.get(job_id)
        if job is None:
            return None
        return self.update(job_id, job.status, job.error, job.attempts + 1)

    def requeue(self, job_id: str) -> Job | None:
        job = self.update(job_id, "queued", "")
        if job is not None and self.client is not None:
            self.client.rpush("jobs:pending", job.job_id)
        return job

    def _save(self, job: Job) -> None:
        self.client.setex(f"job:{job.job_id}", self.ttl_seconds, json.dumps(job.as_dict()))
