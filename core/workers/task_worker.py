"""Redis-backed worker for durable asynchronous LangGraph task execution."""

from typing import Any

from core.graph import build_graph
from core.store.jobs import JobStore
from core.store.redis import save_task_snapshot
from core.store.tasks import TaskStore


def process_job(job_id: str, *, job_store: Any, task_store: Any, graph: Any) -> dict[str, Any]:
    job = job_store.get(job_id)
    if job is None:
        raise ValueError(f"Job '{job_id}' was not found.")

    job_store.update(job_id, "running")
    record = task_store.get(job.task_id)
    if record is None:
        job_store.update(job_id, "failed", "Task metadata was not found.")
        raise ValueError(f"Task '{job.task_id}' was not found.")

    try:
        result = graph.invoke(
            {
                "task": record.task,
                "repository": record.repository,
                "ref": record.ref,
                "task_id": record.task_id,
                "evidence": [],
                "findings": [],
                "tool_calls": [],
                "status": "started",
                "observability_events": [{"event": "async_task_started"}],
            },
            config={"configurable": {"thread_id": record.task_id}},
        )
        save_task_snapshot(record.task_id, result)
        task_store.update(record.task_id, status=result.get("status", "completed"))
        job_store.update(job_id, "completed")
        return result
    except Exception as exc:
        task_store.update(record.task_id, status="failed", error=str(exc))
        job_store.update(job_id, "failed", str(exc))
        raise


def run_worker(*, job_store: Any | None = None, task_store: Any | None = None, graph: Any | None = None) -> None:
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
        process_job(job_id, job_store=jobs, task_store=tasks, graph=runtime)


if __name__ == "__main__":
    run_worker()
