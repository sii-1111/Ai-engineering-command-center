from dataclasses import replace

import pytest

from core.workers.task_worker import process_job


class FakeJobStore:
    def __init__(self, job):
        self.job = job
        self.updates = []
        self.client = object()

    def get(self, job_id):
        return self.job if self.job and self.job.job_id == job_id else None

    def update(self, job_id, status, error=""):
        self.updates.append((job_id, status, error))
        self.job = replace(self.job, status=status, error=error)
        return self.job


class FakeTaskStore:
    def __init__(self, record):
        self.record = record
        self.updates = []

    def get(self, task_id):
        return self.record if self.record and self.record.task_id == task_id else None

    def update(self, task_id, **changes):
        self.updates.append((task_id, changes))
        for key, value in changes.items():
            setattr(self.record, key, value)
        return self.record


class FakeGraph:
    def __init__(self, result=None, error=None):
        self.result = result or {"status": "completed"}
        self.error = error
        self.calls = []

    def invoke(self, state, config):
        self.calls.append((state, config))
        if self.error:
            raise self.error
        return self.result


class Job:
    def __init__(self, job_id="job-1", task_id="task-1", status="queued", error=""):
        self.job_id = job_id
        self.task_id = task_id
        self.status = status
        self.error = error


class Task:
    def __init__(self):
        self.task_id = "task-1"
        self.task = "Investigate the search latency"
        self.repository = "org/repo"
        self.ref = "main"
        self.status = "started"
        self.error = ""


def test_process_job_runs_graph_and_marks_job_complete(monkeypatch):
    snapshots = []
    monkeypatch.setattr("core.workers.task_worker.save_task_snapshot", lambda task_id, result: snapshots.append((task_id, result)))
    jobs = FakeJobStore(Job())
    tasks = FakeTaskStore(Task())
    graph = FakeGraph({"status": "awaiting_approval"})

    result = process_job("job-1", job_store=jobs, task_store=tasks, graph=graph)

    assert result["status"] == "awaiting_approval"
    assert jobs.updates == [("job-1", "running", ""), ("job-1", "completed", "")]
    assert tasks.updates[0] == ("task-1", {"status": "awaiting_approval"})
    assert snapshots == [("task-1", result)]
    assert graph.calls[0][0]["task_id"] == "task-1"
    assert graph.calls[0][1]["configurable"]["thread_id"] == "task-1"


def test_process_job_marks_failure_and_preserves_error(monkeypatch):
    monkeypatch.setattr("core.workers.task_worker.save_task_snapshot", lambda *_: None)
    jobs = FakeJobStore(Job())
    tasks = FakeTaskStore(Task())
    graph = FakeGraph(error=RuntimeError("GitHub unavailable"))

    with pytest.raises(RuntimeError, match="GitHub unavailable"):
        process_job("job-1", job_store=jobs, task_store=tasks, graph=graph)

    assert jobs.updates[-1] == ("job-1", "failed", "GitHub unavailable")
    assert tasks.updates[-1] == ("task-1", {"status": "failed", "error": "GitHub unavailable"})


def test_process_job_rejects_missing_job():
    jobs = FakeJobStore(None)
    tasks = FakeTaskStore(Task())
    with pytest.raises(ValueError, match="was not found"):
        process_job("missing", job_store=jobs, task_store=tasks, graph=FakeGraph())


def test_process_job_fails_when_task_metadata_is_missing(monkeypatch):
    monkeypatch.setattr("core.workers.task_worker.save_task_snapshot", lambda *_: None)
    jobs = FakeJobStore(Job())
    tasks = FakeTaskStore(None)
    with pytest.raises(ValueError, match="Task 'task-1' was not found"):
        process_job("job-1", job_store=jobs, task_store=tasks, graph=FakeGraph())
    assert jobs.updates[-1] == ("job-1", "failed", "Task metadata was not found.")
