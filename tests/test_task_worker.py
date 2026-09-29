from dataclasses import dataclass, replace

import pytest

from core.workers.task_worker import process_job


class FakeJobStore:
    def __init__(self, job):
        self.job = job
        self.updates = []
        self.client = object()

    def get(self, job_id):
        return self.job if self.job and self.job.job_id == job_id else None

    def update(self, job_id, status, error="", attempts=None):
        self.updates.append((job_id, status, error, attempts))
        self.job = replace(self.job, status=status, error=error, attempts=self.job.attempts if attempts is None else attempts)
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
    def __init__(self, results=None, errors=None):
        self.results = list(results or [{"status": "completed"}])
        self.errors = list(errors or [])
        self.calls = 0

    def invoke(self, state, config):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return self.results.pop(0)


@dataclass
class Job:
    job_id: str = "job-1"
    task_id: str = "task-1"
    status: str = "queued"
    error: str = ""
    attempts: int = 0


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
    jobs, tasks, graph = FakeJobStore(Job()), FakeTaskStore(Task()), FakeGraph()
    result = process_job("job-1", job_store=jobs, task_store=tasks, graph=graph, sleep=lambda _: None)
    assert result["status"] == "completed"
    assert jobs.job.status == "completed"
    assert jobs.job.attempts == 1
    assert snapshots == [("task-1", result)]


def test_process_job_retries_transient_failure(monkeypatch):
    monkeypatch.setattr("core.workers.task_worker.save_task_snapshot", lambda *_: None)
    jobs, tasks = FakeJobStore(Job()), FakeTaskStore(Task())
    graph = FakeGraph(errors=[RuntimeError("temporary" )])
    delays = []
    result = process_job("job-1", job_store=jobs, task_store=tasks, graph=graph, sleep=delays.append)
    assert result["status"] == "completed"
    assert graph.calls == 2
    assert delays == [1.0]
    assert jobs.job.attempts == 2
    assert any(status == "retrying" for _, status, _, _ in jobs.updates)


def test_process_job_exhausts_retries_and_records_terminal_failure(monkeypatch):
    monkeypatch.setattr("core.workers.task_worker.save_task_snapshot", lambda *_: None)
    jobs, tasks = FakeJobStore(Job()), FakeTaskStore(Task())
    graph = FakeGraph(errors=[RuntimeError("temporary-1"), RuntimeError("temporary-2"), RuntimeError("terminal")])
    delays = []
    with pytest.raises(RuntimeError, match="terminal"):
        process_job("job-1", job_store=jobs, task_store=tasks, graph=graph, sleep=delays.append)
    assert graph.calls == 3
    assert delays == [1.0, 2.0]
    assert jobs.job.status == "failed"
    assert jobs.job.attempts == 3
    assert tasks.record.status == "failed"
    assert tasks.record.error == "terminal"


def test_process_job_rejects_missing_job():
    with pytest.raises(ValueError, match="was not found"):
        process_job("missing", job_store=FakeJobStore(None), task_store=FakeTaskStore(Task()), graph=FakeGraph())


def test_process_job_fails_when_task_metadata_is_missing():
    jobs = FakeJobStore(Job())
    with pytest.raises(ValueError, match="Task 'task-1' was not found"):
        process_job("job-1", job_store=jobs, task_store=FakeTaskStore(None), graph=FakeGraph())
    assert jobs.job.status == "failed"
