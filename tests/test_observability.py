from core.observability import record_event, record_tool_event, summarize_observability
from core.observability_sink import ObservabilitySink


class FakeRedis:
    def __init__(self):
        self.values = {}

    def setex(self, key, ttl, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)


def test_observability_is_bounded():
    state = {}
    for index in range(205):
        state = record_event(state, "step", index=index)
    assert len(state["observability_events"]) == 200
    assert state["observability_events"][0]["index"] == 5


def test_tool_metrics_are_summarized():
    state = record_tool_event({}, tool="github.search", duration_ms=12.345, success=True, total_tokens=100)
    state = record_tool_event(state, tool="github.read", duration_ms=7.655, success=False, total_tokens=50)
    summary = summarize_observability(state)
    assert summary["tool_call_count"] == 2
    assert summary["total_duration_ms"] == 20.0
    assert summary["total_tokens"] == 150


def test_redis_observability_sink_round_trip():
    sink = ObservabilitySink(client=FakeRedis())
    events = [{"event": "tool_completed"}]
    assert sink.write("task-1", events)
    assert sink.read("task-1") == events


def test_sink_is_optional_without_redis():
    assert ObservabilitySink(client=None).write("task-1", []) is False
