from typing import TypedDict


class Evidence(TypedDict):
    source: str
    detail: str


class EngineeringReport(TypedDict):
    root_cause: str
    evidence: list[str]
    impact: str
    recommended_change: str
    files_involved: list[str]
    confidence: float
    approval_required: bool


class EngineeringState(TypedDict, total=False):
    task: str
    repository: str
    ref: str
    plan: list[str]
    dynamic_plan: list[dict]
    current_step: int
    evidence: list[Evidence]
    findings: list[str]
    tool_calls: list[dict]
    status: str
    final_report: str
    report: EngineeringReport
