from core.mcp_client import call_github_tool_sync
from core.state.models import EngineeringState

ALLOWED_TOOLS = {"search_code", "list_repository", "read_file"}


def execute_dynamic_plan(state: EngineeringState) -> EngineeringState:
    evidence = list(state.get("evidence", []))
    calls = list(state.get("tool_calls", []))
    repository = state["repository"]
    ref = state.get("ref", "main")

    for step in state.get("dynamic_plan", []):
        tool = step.get("tool")
        if tool not in ALLOWED_TOOLS:
            continue
        args = dict(step.get("arguments", {}))
        args.setdefault("repository", repository)
        if tool in {"read_file", "list_repository"}:
            args.setdefault("ref", ref)
        result = call_github_tool_sync(tool, args)
        evidence.append({"source": f"github://{repository}/{tool}", "detail": result})
        calls.append({"tool": f"github.{tool}", "arguments": args})

    return {**state, "evidence": evidence, "tool_calls": calls, "status": "investigation_complete"}
