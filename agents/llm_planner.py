import json
from typing import Any

from core.llm import LLM
from core.state.models import EngineeringReport, EngineeringState

MAX_ITERATIONS = 8
MAX_TOOL_CALLS = 10

TOOL_DESCRIPTIONS = """Available read-only GitHub tools:
- search_code: find relevant code; requires GITHUB_TOKEN. Arguments: {repository, query}.
- read_file: inspect a source file. Arguments: {repository, path, ref}.
- list_repository: explore a repository directory. Arguments: {repository, path, ref}.
- search_repository_rag: retrieve repository code chunks using the local repository retrieval index. Arguments: {repository, query, ref, top_k}.\n- search_engineering_knowledge: retrieve prior verified engineering findings. Arguments: {repository, query, top_k}.
For public repositories without GITHUB_TOKEN, prefer list_repository and read_file.
"""

PLANNER_SYSTEM = f"""You are an AI software engineering investigator.
Choose the FIRST minimal read-only investigation action for the task.
Return JSON only: {{"tool":"search_code|list_repository|read_file|search_repository_rag|search_engineering_knowledge","arguments":{{...}}}}.
Never modify files. Use search_code only when GITHUB_TOKEN is configured.
{TOOL_DESCRIPTIONS}"""

DECISION_SYSTEM = f"""You are an AI software engineering investigator working iteratively.
Review the task and accumulated evidence, then choose exactly ONE next read-only GitHub action,
or finish if the evidence is sufficient.
Return JSON only in one of these forms:
{{"action":"tool","tool":"search_code|list_repository|read_file|search_repository_rag|search_engineering_knowledge","arguments":{{...}}}}
or
{{"action":"finish","report":{{"root_cause":"...","evidence":["exact evidence details"],"impact":"...","recommended_change":"...","files_involved":["path"],"confidence":0.0,"approval_required":false}}}}
Rules for a finished report:
- Do not finish until at least 3 successful read-only tool calls have been collected, unless a tool fails or the repository is inaccessible.
- Prefer a layered investigation: start with repository structure, then inspect relevant source/configuration files, then cross-check with search or repository RAG when useful.
- When the repository structure is known, inspect concrete files rather than repeatedly listing the same directory.
- In a finished report, cite evidence by evidence ID (for example "ev-003"). The evidence catalog is supplied with stable IDs.
- Root cause must be a causal explanation, not merely a restatement of the task.
- Confidence must be a number from 0.0 to 1.0.
- List only files supported by the cited evidence.
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

def _successful_tool_call_count(state: EngineeringState) -> int:
    evidence_by_id = {item.get("id"): item for item in state.get("evidence", [])}
    return sum(
        1
        for call in state.get("tool_calls", [])
        if call.get("status") == "success"
        and str(evidence_by_id.get(call.get("id"), {}).get("detail", "")).strip()
    )


def _fallback_investigation_tool(state: EngineeringState) -> dict:
    inspected_paths = {
        str(call.get("arguments", {}).get("path"))
        for call in state.get("tool_calls", [])
        if call.get("tool") == "github.read_file"
    }
    candidates = ["core/graph.py", "agents/llm_planner.py", "apps/web/app/page.tsx", "pyproject.toml", "README.md"]

    for item in state.get("evidence", []):
        if item.get("source", "").endswith("/list_repository"):
            try:
                entries = json.loads(item.get("detail", ""))
            except (TypeError, ValueError):
                entries = []
            if isinstance(entries, list):
                candidates = [
                    str(entry.get("path"))
                    for entry in entries
                    if entry.get("type") == "file" and entry.get("path")
                ] + candidates
                break

    for path in candidates:
        if path and path not in inspected_paths:
            return {"tool": "read_file", "arguments": {"repository": state["repository"], "path": path, "ref": state.get("ref", "main")}}
    return {"tool": "list_repository", "arguments": {"repository": state["repository"], "path": "", "ref": state.get("ref", "main")}}


def _bounded_tool_calls(state: EngineeringState) -> bool:
    return len(state.get("tool_calls", [])) >= MAX_TOOL_CALLS or state.get("current_step", 0) >= MAX_ITERATIONS


def _normalize_report(raw: dict[str, Any], evidence: list[dict[str, str]]) -> EngineeringReport:
    evidence_by_id = {item.get("id", ""): item for item in evidence if item.get("id")}
    cited_items: list[dict[str, str]] = []
    requested_evidence = raw.get("evidence", [])

    for reference in requested_evidence:
        key = str(reference)
        if key in evidence_by_id:
            cited_items.append(evidence_by_id[key])
            continue
        # Backward-compatible exact/substring matching for legacy model outputs.
        for item in evidence:
            detail = item.get("detail", "")
            if key == detail or (key and key in detail):
                cited_items.append(item)
                break

    cited = [item.get("detail", "") for item in cited_items if item.get("detail")]
    if not cited:
        collected = [
            item.get("detail", "")
            for item in evidence
            if item.get("detail")
            and not item.get("detail", "").startswith("Error executing tool")
            and '"error"' not in item.get("detail", "")
        ][:6]
        return {
            "root_cause": "The model did not provide a conclusion supported by cited evidence.",
            "evidence": collected,
            "impact": "No reliable impact assessment was produced.",
            "recommended_change": "Review the collected evidence and retry with a focused task.",
            "files_involved": [],
            "confidence": 0.0,
            "approval_required": False,
        }

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
    usable_evidence_count = _successful_tool_call_count(state)
    if usable_evidence_count < 3:
        context_note = (
            "You MUST choose another read-only tool because fewer than 3 successful tool calls "
            "with non-empty evidence have been collected. Empty tool responses do not count."
        )
    else:
        context_note = "You may finish only when the evidence is sufficient and directly supports a conclusion; otherwise choose another tool."

    context = json.dumps({
        "task": state["task"], "repository": state["repository"], "ref": state.get("ref", "main"),
        "instruction": context_note,
        "tool_calls": state.get("tool_calls", []),
        "evidence": [
            {"id": item.get("id"), "source": item.get("source"), "detail": item.get("detail", "")[:12000]}
            for item in state.get("evidence", [])
        ],
    })
    decision = LLM().invoke_json([
        {"role": "system", "content": DECISION_SYSTEM},
        {"role": "user", "content": context},
    ])
    if decision.get("action") == "finish":
        if usable_evidence_count < 3:
            fallback = _fallback_investigation_tool(state)
            return {**state,
                    "dynamic_plan": [fallback],
                    "current_step": state.get("current_step", 0) + 1,
                    "status": "ready_to_execute"}
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
