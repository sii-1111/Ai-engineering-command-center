"""Reliable Redis-backed worker for durable LangGraph task execution."""

import os
import time
from typing import Any

from core.graph import build_graph
from core.store.jobs import JobStore
from core.store.redis import save_task_snapshot
from core.store.tasks import TaskStore

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = 1.0


def process_job(job_id: str, *, job_store: Any, task_store: Any, graph: Any, max_attempts: int = DEFAULT_MAX_ATTEMPTS, backoff_seconds: float = DEFAULT_BACKOFF_SECONDS, sleep: Any = time.sleep) -> dict[str, Any] | None:
    job = job_store.get(job_id)
    if job is None:
        raise ValueError(f"Job '{job_id}' was not found.")
    record = task_store.get(job.task_id)
    if record is None:
        job_store.update(job_id, "failed", "Task metadata was not found.")
        raise ValueError(f"Task '{job.task_id}' was not found.")

    for attempt in range(job.attempts + 1, max_attempts + 1):
        job_store.update(job_id, "running", "", attempts=attempt)
        try:
            result = graph.invoke(
                {"task": record.task, "repository": record.repository, "ref": record.ref, "task_id": record.task_id, "evidence": [], "findings": [], "tool_calls": [], "status": "started", "observability_events": [{"event": "async_task_started", "attempt": attempt}]},
                config={"configurable": {"thread_id": record.task_id}},
            )
            save_task_snapshot(record.task_id, result)
            task_store.update(record.task_id, status=result.get("status", "completed"), error="")
            job_store.update(job_id, "completed", "", attempts=attempt)
            return result
        except Exception as exc:
            message = str(exc)
            if attempt >= max_attempts:
                task_store.update(record.task_id, status="failed", error=message)
                job_store.update(job_id, "failed", message, attempts=attempt)
                raise
            job_store.update(job_id, "retrying", message, attempts=attempt)
            sleep(backoff_seconds * (2 ** (attempt - 1)))
    return None


def run_worker(*, job_store: Any | None = None, task_store: Any | None = None, graph: Any | None = None, max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> None:
    jobs = job_store or JobStore()
    tasks = task_store or TaskStore()
    runtime = graph or build_graph()
    if jobs.client is None:
        raise RuntimeError("REDIS_URL must be configured for the task worker.")
    while True:
        item = jobs.client.blpop("jobs:pending", timeout=5)
        if not item:
            continue
        _, job_id = item
        try:
            process_job(job_id, job_store=jobs, task_store=tasks, graph=runtime, max_attempts=max_attempts)
        except Exception:
            continue


if __name__ == "__main__":
    run_worker(max_attempts=int(os.getenv("WORKER_MAX_ATTEMPTS", str(DEFAULT_MAX_ATTEMPTS))))
