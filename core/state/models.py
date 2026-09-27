from typing import TypedDict


class Evidence(TypedDict):
    source: str
    detail: str


class EngineeringState(TypedDict, total=False):
    task: str
    plan: list[str]
    current_step: int
    evidence: list[Evidence]
    findings: list[str]
    tool_calls: list[dict]
    status: str
    final_report: str
