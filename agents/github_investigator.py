import json

from core.mcp_client import call_github_tool_sync
from core.state.models import EngineeringState


def inspect_repository(state: EngineeringState) -> EngineeringState:
    repository = state["repository"]
    ref = state.get("ref", "main")
    evidence = list(state.get("evidence", []))
    calls = list(state.get("tool_calls", []))

    search = call_github_tool_sync(
        "search_code",
        {"repository": repository, "query": state["task"]},
    )
    evidence.append({
        "source": f"github://{repository}/code-search",
        "detail": search,
    })
    calls.append({
        "tool": "github.search_code",
        "arguments": {"repository": repository, "query": state["task"]},
    })

    listing = call_github_tool_sync(
        "list_repository",
        {"repository": repository, "path": "", "ref": ref},
    )
    evidence.append({
        "source": f"github://{repository}/tree/{ref}",
        "detail": listing,
    })
    calls.append({
        "tool": "github.list_repository",
        "arguments": {"repository": repository, "ref": ref},
    })

    return {
        **state,
        "evidence": evidence,
        "tool_calls": calls,
        "status": "github_inspected",
    }


def add_findings(state: EngineeringState) -> EngineeringState:
    matches: list[str] = []
    for evidence in state.get("evidence", []):
        if evidence["source"].endswith("/code-search"):
            try:
                payload = json.loads(evidence["detail"])
                matches = [item["path"] for item in payload.get("matches", []) if item.get("path")]
            except (ValueError, KeyError, TypeError):
                matches = []

    finding = (
        f"GitHub code search returned {len(matches)} matching file(s): {matches[:10]}"
    )
    return {**state, "findings": [*state.get("findings", []), finding]}
