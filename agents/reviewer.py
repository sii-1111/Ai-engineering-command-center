import json
from typing import Any

from core.llm import LLM
from core.state.models import EngineeringState, ReviewResult

REVIEW_SYSTEM = """You are a senior software reviewer/critic.
Review an AI-generated engineering investigation and proposed change using only the supplied task, evidence, report, change plan, and verification result.
Return JSON only:
{"decision":"approve|request_changes|reject","summary":"...","findings":[{"severity":"critical|high|medium|low","category":"correctness|evidence|scope|safety|testing","message":"..."}],"confidence":0.0}
Rules:
- Do not invent repository facts or evidence.
- Check whether the proposed change directly addresses the reported root cause.
- Check that the change is limited to the approved file and preserves unrelated behavior.
- Treat missing/failed verification as a testing finding.
- A critical or high correctness/safety issue should produce request_changes or reject.
- Confidence must be between 0.0 and 1.0.
"""


def _normalize_review(raw: dict[str, Any]) -> ReviewResult:
    decision = str(raw.get("decision", "request_changes"))
    if decision not in {"approve", "request_changes", "reject"}:
        decision = "request_changes"
    findings = []
    for item in raw.get("findings", []):
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity", "medium"))
        if severity not in {"critical", "high", "medium", "low"}:
            severity = "medium"
        findings.append({
            "severity": severity,
            "category": str(item.get("category", "correctness")),
            "message": str(item.get("message", "")),
        })
    try:
        confidence = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "decision": decision,
        "summary": str(raw.get("summary", "")),
        "findings": findings,
        "confidence": max(0.0, min(1.0, confidence)),
    }


def review_change(state: EngineeringState) -> EngineeringState:
    context = {
        "task": state.get("task", ""),
        "report": state.get("report", {}),
        "evidence": state.get("evidence", []),
        "change_plan": state.get("change_plan", {}),
        "verification_status": state.get("verification_status", "not_started"),
        "verification_result": state.get("verification_result", {}),
    }
    raw = LLM().invoke_json([
        {"role": "system", "content": REVIEW_SYSTEM},
        {"role": "user", "content": json.dumps(context)},
    ])
    review = _normalize_review(raw)
    return {**state, "review": review, "status": f"review_{review['decision']}"}
