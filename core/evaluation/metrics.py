from typing import Any

from core.observability import record_event


def evaluate_task(state: dict[str, Any]) -> dict[str, Any]:
    report = state.get("report", {})
    review = state.get("review", {})
    verification = state.get("verification_result", {})
    events = state.get("observability_events", [])
    tool_calls = state.get("tool_calls", [])
    evidence = state.get("evidence", [])

    completed_checks = [
        item for item in verification.get("checks", [])
        if item.get("status") == "completed"
    ]
    evaluation = {
        "task_completed": state.get("status") in {"review_approve", "review_request_changes", "review_reject"},
        "investigation": {
            "evidence_count": len(evidence),
            "tool_call_count": len(tool_calls),
            "report_confidence": report.get("confidence", 0.0),
        },
        "change": {
            "approval_status": state.get("approval_status", "not_required"),
            "verification_status": state.get("verification_status", "not_started"),
            "checks_completed": len(completed_checks),
        },
        "review": {
            "decision": review.get("decision", "not_run"),
            "confidence": review.get("confidence", 0.0),
            "finding_count": len(review.get("findings", [])),
        },
        "observability": {
            "event_count": len(events),
        },
    }
    updated = record_event(state, "evaluation_completed", metrics=evaluation)
    return {**updated, "evaluation": evaluation, "status": state.get("status", "completed")}
