from core.mcp_client import call_github_tool_sync
from core.state.models import EngineeringState

READ_ONLY_TOOLS = {"search_code", "list_repository", "read_file"}


def execute_next_tool(state: EngineeringState) -> EngineeringState:
    evidence = list(state.get("evidence", []))
    calls = list(state.get("tool_calls", []))
    repository = state["repository"]
    ref = state.get("ref", "main")
    step = (state.get("dynamic_plan") or [{}])[0]
    tool = step.get("tool")

    if tool not in READ_ONLY_TOOLS:
        return {**state, "status": "investigation_complete", "report": {
            "root_cause": "Planner selected an unsupported tool.",
            "evidence": [],
            "impact": "Investigation stopped safely.",
            "recommended_change": "Use one of the registered read-only GitHub tools.",
            "files_involved": [],
            "confidence": 0.0,
            "approval_required": False,
        }}

    args = dict(step.get("arguments", {}))
    args.setdefault("repository", repository)
    if tool in {"read_file", "list_repository"}:
        args.setdefault("ref", ref)

    result = call_github_tool_sync(tool, args)
    evidence.append({"source": f"github://{repository}/{tool}", "detail": result})
    calls.append({"tool": f"github.{tool}", "arguments": args})

    return {
        **state,
        "evidence": evidence,
        "tool_calls": calls,
        "status": "evidence_ready",
    }
