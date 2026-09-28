import json

from core.llm import LLM
from core.state.models import EngineeringState

MAX_ITERATIONS = 8
MAX_TOOL_CALLS = 10

TOOL_DESCRIPTIONS = """Available read-only GitHub tools:
- search_code: find relevant code. Arguments: {repository, query}.
- read_file: inspect a source file. Arguments: {repository, path, ref}.
- list_repository: explore a repository directory. Arguments: {repository, path, ref}.
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
{{"action":"finish","report":{{"root_cause":"...","evidence":["..."],"impact":"...","recommended_change":"...","files_involved":["..."],"confidence":0.0,"approval_required":false}}}}
Do not invent evidence. Keep the investigation focused.
{TOOL_DESCRIPTIONS}"""


def _bounded_tool_calls(state: EngineeringState) -> bool:
    return len(state.get("tool_calls", [])) >= MAX_TOOL_CALLS or state.get("current_step", 0) >= MAX_ITERATIONS


def build_dynamic_plan(state: EngineeringState) -> EngineeringState:
    prompt = json.dumps({
        "task": state["task"],
        "repository": state["repository"],
        "ref": state.get("ref", "main"),
    })
    plan = LLM().invoke_json([
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": prompt},
    ])
    step = {"tool": plan.get("tool"), "arguments": plan.get("arguments", {})}
    return {
        **state,
        "dynamic_plan": [step],
        "current_step": 0,
        "status": "ready_to_execute",
    }


def decide_next_action(state: EngineeringState) -> EngineeringState:
    if _bounded_tool_calls(state):
        return {
            **state,
            "status": "investigation_complete",
            "report": {
                "root_cause": "Investigation reached the configured execution bound.",
                "evidence": [item["detail"] for item in state.get("evidence", [])],
                "impact": "Root cause was not conclusively established within the execution bound.",
                "recommended_change": "Review the collected evidence and continue with a targeted investigation.",
                "files_involved": [],
                "confidence": 0.0,
                "approval_required": False,
            },
        }

    context = json.dumps({
        "task": state["task"],
        "repository": state["repository"],
        "ref": state.get("ref", "main"),
        "tool_calls": state.get("tool_calls", []),
        "evidence": state.get("evidence", []),
    })
    decision = LLM().invoke_json([
        {"role": "system", "content": DECISION_SYSTEM},
        {"role": "user", "content": context},
    ])

    if decision.get("action") == "finish":
        return {**state, "status": "investigation_complete", "report": decision.get("report", {})}

    return {
        **state,
        "dynamic_plan": [
            {"tool": decision.get("tool"), "arguments": decision.get("arguments", {})}
        ],
        "current_step": state.get("current_step", 0) + 1,
        "status": "ready_to_execute",
    }
