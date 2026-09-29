"""API helpers for task observability."""

from core.observability import summarize_observability
from core.observability_sink import ObservabilitySink

_sink = ObservabilitySink()


def get_task_observability(task_id: str, state: dict) -> dict:
    events = state.get("observability_events", [])
    durable = _sink.read(task_id)
    if durable:
        events = durable
    return {
        "task_id": task_id,
        "summary": summarize_observability({**state, "observability_events": events}),
        "events": events,
    }
