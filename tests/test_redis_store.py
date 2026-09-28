from core.store.redis import get_task_snapshot, healthcheck, save_task_snapshot


def test_redis_store_is_optional_without_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert save_task_snapshot("task-1", {"status": "started"}) is False
    assert get_task_snapshot("task-1") is None
    assert healthcheck() is False
