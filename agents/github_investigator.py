import json
from core.mcp_client import call_github_tool_sync
from core.state.models import EngineeringState


def inspect_repository(state: EngineeringState) -> EngineeringState:
    repository = state["repository"]
    ref = state.get("ref", "main")
    evidence = list(state.get("evidence", []))
    calls = list(state.get("tool_calls", []))

    search = call_github_tool_sync("search_code", {"repository": repository, "query": state["task"]})
    evidence.append({"source": f"github://{repository}/code-search", "detail": search})
    calls.append({"tool": "github.search_code", "repository": repository})

    listing = call_github_tool_sync("list_repository", {"repository": repository, "path": "", "ref": ref})
    evidence.append({"source": f"github://{repository}/tree/{ref}", "detail": listing})
    calls.append({"tool": "github.list_repository", "repository": repository})

    return {**state, "evidence": evidence, "tool_calls": calls, "status": "github_inspected"}


def add_findings(state: EngineeringState) -> EngineeringState:
    matches = []
    for evidence in state.get("evidence", []):
        if evidence["source"].endswith("/code-search"):
            try:
                matches = [x["path"] for x in json.loads(evidence["detail"]).get("matches", [])]
            except (ValueError, KeyError):
                pass
    finding = f"GitHub code search returned {len(matches)} matching file(s): {matches[:10]}"
    return {**state, "findings": [*state.get("findings", []), finding]}
