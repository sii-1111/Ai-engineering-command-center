from core.graph import _build_checkpointer


def test_graph_uses_memory_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    checkpointer = _build_checkpointer()
    assert checkpointer.__class__.__name__ == "InMemorySaver"
