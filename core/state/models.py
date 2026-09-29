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


class ReviewFinding(TypedDict):
    severity: str
    category: str
    message: str


class ReviewResult(TypedDict):
    decision: str
    summary: str
    findings: list[ReviewFinding]
    confidence: float


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
    approval_status: str
    approval_request: dict
    change_plan: dict
    change_branch: str
    change_result: dict
    pull_request: dict
    verification_status: str
    verification_result: dict
    review: ReviewResult
    observability_events: list[dict]
    evaluation: dict
    memory_summary: str
    memory_decisions: list[dict]
