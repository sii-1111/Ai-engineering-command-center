from core.memory.knowledge import EngineeringKnowledge, InMemoryKnowledgeStore, knowledge_from_state
from core.memory.promotion import promote_knowledge


def _state(**overrides):
    state = {
        "task": "fix cache invalidation",
        "repository": "sii-1111/example",
        "ref": "main",
        "report": {
            "root_cause": "stale cache key",
            "recommended_change": "include tenant in cache key",
            "files_involved": ["cache.py"],
            "confidence": 0.9,
        },
        "verification_status": "passed",
        "verification_result": {"checks": [{"status": "completed", "conclusion": "success"}]},
        "review": {"decision": "approve", "confidence": 0.95},
        "pull_request": {"url": "https://github.com/example/pr/1"},
    }
    state.update(overrides)
    return state


def test_knowledge_requires_verification_and_approval():
    assert knowledge_from_state(_state(verification_status="failed")) is None
    assert knowledge_from_state(_state(review={"decision": "request_changes"})) is None


def test_knowledge_from_verified_state_contains_provenance():
    knowledge = knowledge_from_state(_state())
    assert knowledge is not None
    assert knowledge.repository == "sii-1111/example"
    assert knowledge.files == ("cache.py",)
    assert knowledge.pull_request.endswith("/1")


def test_in_memory_store_is_repository_scoped():
    store = InMemoryKnowledgeStore()
    store.save(EngineeringKnowledge(
        knowledge_id="1", task_id="t1", repository="org/a", ref="main",
        root_cause="cache key mismatch", fix="include tenant", tags=("cache",),
    ))
    store.save(EngineeringKnowledge(
        knowledge_id="2", task_id="t2", repository="org/b", ref="main",
        root_cause="database timeout", fix="add index", tags=("database",),
    ))
    results = store.search("cache", repository="org/a")
    assert [item.knowledge_id for item in results] == ["1"]


def test_promotion_writes_only_verified_approved_knowledge(monkeypatch):
    store = InMemoryKnowledgeStore()
    monkeypatch.setattr("core.memory.promotion.get_knowledge_store", lambda: store)

    result = promote_knowledge(_state())
    assert result["knowledge_promoted"] is True
    assert len(store.search("cache")) == 1

    rejected = promote_knowledge(_state(review={"decision": "reject"}))
    assert rejected["knowledge_promoted"] is False
    assert len(store.search("cache")) == 1
