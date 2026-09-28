from datetime import UTC, datetime
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def record_event(state: dict[str, Any], event: str, **data: Any) -> dict[str, Any]:
    events = list(state.get("observability_events", []))
    events.append({"timestamp": utc_now(), "event": event, **data})
    return {**state, "observability_events": events}
