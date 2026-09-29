from core.store.jobs import JobStore
from core.store.tasks import TaskRecord, TaskStore


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.lists = {}

    def setex(self, key, ttl, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        return int(key in self.values)

    def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)


def test_task_store_persists_metadata_and_updates():
    store = TaskStore(client=FakeRedis(), ttl_seconds=60)
    record = TaskRecord("t1", "find bug", "org/repo", "main")
    assert store.save(record)
    assert store.get("t1").status == "started"
    updated = store.update("t1", status="completed")
    assert updated.status == "completed"


def test_task_store_is_optional_without_redis():
    store = TaskStore(client=None)
    assert store.save(TaskRecord("t1", "task", "org/repo", "main")) is False
    assert store.get("t1") is None


def test_job_store_enqueues_and_tracks_state():
    store = JobStore(client=FakeRedis(), ttl_seconds=60)
    job = store.enqueue("t1")
    assert job.status == "queued"
    assert store.get(job.job_id).task_id == "t1"
    assert store.update(job.job_id, "running").status == "running"
