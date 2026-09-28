from uuid import uuid4

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

    return {**state, "evidence": evidence, "tool_calls": calls, "status": "evidence_ready"}


def execute_approved_change(state: EngineeringState) -> EngineeringState:
    if state.get("approval_status") != "approved":
        return {**state, "status": "rejected", "change_result": {"error": "Change was not approved."}}

    plan = state.get("change_plan", {})
    path = str(plan.get("path", ""))
    if not path or path.startswith("/") or ".." in path.split("/"):
        return {**state, "status": "change_failed", "change_result": {"error": "Invalid repository path."}}

    branch = f"ai-fix-{uuid4().hex[:8]}"
    repository = state["repository"]
    base = state.get("ref", "main")
    try:
        branch_result = call_github_tool_sync(
            "create_branch", {"repository": repository, "branch": branch, "base_ref": base}
        )
        current = call_github_tool_sync(
            "read_file", {"repository": repository, "path": path, "ref": base}
        )
        import json

        current_data = json.loads(current)
        current_sha = current_data.get("sha")
        if not current_sha:
            raise ValueError("Unable to resolve current file SHA.")

        update_result = call_github_tool_sync("update_file", {
            "repository": repository,
            "path": path,
            "content": str(plan.get("content", "")),
            "branch": branch,
            "message": str(plan.get("commit_message", "feat: apply approved engineering change")),
            "sha": current_sha,
        })
        pr_result = call_github_tool_sync("create_pull_request", {
            "repository": repository,
            "title": str(plan.get("pr_title", "feat: apply approved engineering change")),
            "body": str(plan.get("pr_body", "")),
            "head": branch,
            "base": base,
        })
    except Exception as exc:
        return {
            **state,
            "status": "change_failed",
            "change_branch": branch,
            "change_result": {"error": str(exc), "branch_result": locals().get("branch_result")},
        }

    return {
        **state,
        "status": "change_applied",
        "change_branch": branch,
        "change_result": update_result,
        "pull_request": pr_result,
    }
