import json
from typing import Any

from core.llm import LLM
from core.state.models import EngineeringReport, EngineeringState

MAX_ITERATIONS = 8
MAX_TOOL_CALLS = 10

TOOL_DESCRIPTIONS = """Available read-only GitHub tools:
- search_code: find relevant code. Arguments: {repository, query}.
- read_file: inspect a source file. Arguments: {repository, path, ref}.
- list_repository: explore a repository directory. Arguments: {repository, path, ref}.
- search_repository_rag: retrieve repository code chunks using Azure AI Search hybrid retrieval. Arguments: {repository, query, ref, top_k}.
"""

PLANNER_SYSTEM = f"""You are an AI software engineering investigator.
Choose the FIRST minimal read-only investigation action for the task.
Return JSON only: {{"tool":"search_code|list_repository|read_file","arguments":{{...}}}}.
Never modify files. Prefer search_code for an unknown implementation.
{TOOL_DESCRIPTIONS}"""

DECISION_SYSTEM = f"""You are an AI software engineering investigator working iteratively.
Review the task and accumulated evidence, then choose exactly ONE next read-only GitHub action,
or finish if the evidence is sufficient.
Return JSON only in one of these forms:
{{"action":"tool","tool":"search_code|list_repository|read_file","arguments":{{...}}}}
or
{{"action":"finish","report":{{"root_cause":"...","evidence":["exact evidence details"],"impact":"...","recommended_change":"...","files_involved":["path"],"confidence":0.0,"approval_required":false}}}}
Rules for a finished report:
- Only cite evidence present in the supplied evidence list.
- Root cause must be a causal explanation, not merely a restatement of the task.
- Confidence must be a number from 0.0 to 1.0.
- List only files supported by the evidence.
- Set approval_required=true when the recommended change would modify code, configuration, data, or infrastructure.
- If evidence is insufficient, choose another tool instead of guessing.
Do not invent evidence. Keep the investigation focused.
{TOOL_DESCRIPTIONS}"""

CHANGE_SYSTEM = """You are an AI software engineer preparing an exact, reviewable change after an investigation.
Return JSON only:
{"path":"repo-relative/path","content":"complete new file content","summary":"what changed","commit_message":"...","pr_title":"...","pr_body":"..."}
Rules:
- Change exactly one existing file.
- Path must be one of files_involved.
- Preserve unrelated behavior.
- Provide complete file content, not a diff.
- Do not add secrets, credentials, destructive commands, or generated binaries.
- The change must directly address the recommended_change and be supported by evidence.
"""

def _bounded_tool_calls(state: EngineeringState) -> bool:
    return len(state.get("tool_calls", [])) >= MAX_TOOL_CALLS or state.get("current_step", 0) >= MAX_ITERATIONS


def _normalize_report(raw: dict[str, Any], evidence: list[dict[str, str]]) -> EngineeringReport:
    allowed_details = {item.get("detail", "") for item in evidence}
    cited = [str(item) for item in raw.get("evidence", []) if str(item) in allowed_details]
    try:
        confidence = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    supported_files = [str(path) for path in raw.get("files_involved", []) if str(path)]
    return {
        "root_cause": str(raw.get("root_cause", "Not established")),
        "evidence": cited,
        "impact": str(raw.get("impact", "Not established")),
        "recommended_change": str(raw.get("recommended_change", "None")),
        "files_involved": supported_files,
        "confidence": confidence,
        "approval_required": bool(raw.get("approval_required", False)),
    }


def _bounded_report(state: EngineeringState) -> EngineeringReport:
    return {
        "root_cause": "Investigation reached the configured execution bound.",
        "evidence": [item["detail"] for item in state.get("evidence", [])],
        "impact": "Root cause was not conclusively established within the execution bound.",
        "recommended_change": "Review the collected evidence and continue with a targeted investigation.",
        "files_involved": [],
        "confidence": 0.0,
        "approval_required": False,
    }


def build_dynamic_plan(state: EngineeringState) -> EngineeringState:
    prompt = json.dumps({"task": state["task"], "repository": state["repository"], "ref": state.get("ref", "main")})
    plan = LLM().invoke_json([
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": prompt},
    ])
    step = {"tool": plan.get("tool"), "arguments": plan.get("arguments", {})}
    return {**state, "dynamic_plan": [step], "current_step": 0, "status": "ready_to_execute"}


def decide_next_action(state: EngineeringState) -> EngineeringState:
    if _bounded_tool_calls(state):
        return {**state, "status": "investigation_complete", "report": _bounded_report(state)}
    context = json.dumps({
        "task": state["task"], "repository": state["repository"], "ref": state.get("ref", "main"),
        "tool_calls": state.get("tool_calls", []), "evidence": state.get("evidence", []),
    })
    decision = LLM().invoke_json([
        {"role": "system", "content": DECISION_SYSTEM},
        {"role": "user", "content": context},
    ])
    if decision.get("action") == "finish":
        return {**state, "status": "investigation_complete",
                "report": _normalize_report(decision.get("report", {}), state.get("evidence", []))}
    return {**state,
            "dynamic_plan": [{"tool": decision.get("tool"), "arguments": decision.get("arguments", {})}],
            "current_step": state.get("current_step", 0) + 1,
            "status": "ready_to_execute"}


def prepare_change_plan(state: EngineeringState) -> EngineeringState:
    report = state.get("report", {})
    if not report.get("approval_required", False):
        return {**state, "status": "change_not_required"}
    context = json.dumps({
        "task": state["task"], "repository": state["repository"], "report": report,
        "evidence": state.get("evidence", []),
    })
    plan = LLM().invoke_json([
        {"role": "system", "content": CHANGE_SYSTEM},
        {"role": "user", "content": context},
    ])
    if plan.get("path") not in report.get("files_involved", []):
        return {**state, "status": "change_plan_invalid", "change_plan": {}}
    return {**state, "status": "awaiting_approval", "change_plan": {
        "path": plan.get("path"),
        "content": plan.get("content", ""),
        "summary": plan.get("summary", ""),
        "commit_message": plan.get("commit_message", "feat: apply approved engineering change"),
        "pr_title": plan.get("pr_title", "feat: apply approved engineering change"),
        "pr_body": plan.get("pr_body", ""),
    }}
