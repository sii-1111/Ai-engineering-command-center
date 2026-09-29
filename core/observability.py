"""Structured, bounded observability for agent execution."""

from datetime import UTC, datetime
from typing import Any

MAX_EVENTS = 200


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def record_event(state: dict[str, Any], event: str, **data: Any) -> dict[str, Any]:
    events = list(state.get("observability_events", []))
    events.append({"timestamp": utc_now(), "event": event, **data})
    return {**state, "observability_events": events[-MAX_EVENTS:]}


def summarize_observability(state: dict[str, Any]) -> dict[str, Any]:
    events = state.get("observability_events", [])
    tool_events = [event for event in events if event.get("event") == "tool_completed"]
    durations = [float(event["duration_ms"]) for event in tool_events if "duration_ms" in event]
    total_tokens = sum(int(event.get("total_tokens", 0)) for event in events)
    total_cost = sum(float(event.get("estimated_cost_usd", 0.0)) for event in events)
    return {
        "event_count": len(events),
        "tool_call_count": len(tool_events),
        "total_duration_ms": round(sum(durations), 2),
        "avg_tool_duration_ms": round(sum(durations) / len(durations), 2) if durations else 0.0,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(total_cost, 6),
    }


def record_tool_event(
    state: dict[str, Any],
    *,
    tool: str,
    duration_ms: float,
    success: bool,
    **metadata: Any,
) -> dict[str, Any]:
    return record_event(
        state,
        "tool_completed",
        tool=tool,
        duration_ms=round(duration_ms, 2),
        success=success,
        **metadata,
    )
