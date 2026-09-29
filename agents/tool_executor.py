import json
from uuid import uuid4

from core.mcp_client import call_github_tool_sync
from core.observability import record_event
from core.retrieval.search import search_repository\nfrom core.retrieval.knowledge import search_engineering_knowledge
from core.security.tool_policy import DEFAULT_TOOL_POLICY, ToolPermissionError
from core.state.models import EngineeringState

READ_ONLY_TOOLS = {"search_code", "list_repository", "read_file", "search_repository_rag", "search_engineering_knowledge"}


def _tool_audit(
    state: EngineeringState,
    agent: str,
    tool: str,
    allowed: bool,
    risk: str,
    result: str,
) -> EngineeringState:
    return record_event(
        state,
        "tool_execution",
        agent=agent,
        tool=tool,
        risk=risk,
        approved=allowed,
        result=result,
    )


def _blocked_tool_state(
    state: EngineeringState,
    agent: str,
    tool: str,
    error: ToolPermissionError,
) -> EngineeringState:
    decision = error.decision
    audited = _tool_audit(state, agent, tool, False, decision.risk, "blocked")
    return {
        **audited,
        "status": "investigation_complete",
        "report": {
            "root_cause": "Tool execution was blocked by the agent permission policy.",
            "evidence": [],
            "impact": "Investigation stopped safely before an unauthorized MCP call.",
            "recommended_change": decision.reason,
            "files_involved": [],
            "confidence": 0.0,
            "approval_required": False,
        },
    }


def execute_next_tool(state: EngineeringState) -> EngineeringState:
    evidence = list(state.get("evidence", []))
    calls = list(state.get("tool_calls", []))
    repository = state["repository"]
    ref = state.get("ref", "main")
    step = (state.get("dynamic_plan") or [{}])[0]
    tool = step.get("tool")
    agent = "research_agent"

    try:
        decision = DEFAULT_TOOL_POLICY.enforce(agent, tool)
    except ToolPermissionError as exc:
        return _blocked_tool_state(state, agent, tool, exc)

    args = dict(step.get("arguments", {}))
    args.setdefault("repository", repository)
    if tool in {"read_file", "list_repository"}:
        args.setdefault("ref", ref)

    try:
        if tool == "search_engineering_knowledge":\n            knowledge = search_engineering_knowledge(\n                str(args.get("query", state["task"])), repository=repository, top_k=int(args.get("top_k", 5))\n            )\n            result = json.dumps({"knowledge": knowledge})\n            call_name = "knowledge.search"\n        elif tool == "search_repository_rag":
            rag_results = search_repository(
                str(args.get("query", state["task"])),
                repository=repository,
                ref=ref,
                top_k=int(args.get("top_k", 5)),
            )
            result = json.dumps({"matches": rag_results})
            call_name = "repository.rag"
        else:
            result = call_github_tool_sync(tool, args, agent=agent)
            call_name = f"github.{tool}"
    except ToolPermissionError as exc:
        return _blocked_tool_state(state, agent, tool, exc)
    except (ValueError, RuntimeError) as exc:
        evidence.append({
            "source": f"repository-rag://{repository}/{ref}",
            "detail": json.dumps({"error": str(exc)}),
        })
        calls.append({
            "tool": "repository.rag",
            "arguments": {"repository": repository, "ref": ref, "query": args.get("query", state["task"])},
            "status": "failed",
        })
        audited = _tool_audit(state, agent, tool, True, decision.risk, "failed")
        return {**audited, "evidence": evidence, "tool_calls": calls, "status": "evidence_ready"}

    evidence.append({"source": f"{call_name}://{repository}/{tool}", "detail": result})
    calls.append({"tool": call_name, "arguments": args})
    audited = _tool_audit(state, agent, tool, True, decision.risk, "success")

    return {**audited, "evidence": evidence, "tool_calls": calls, "status": "evidence_ready"}


def execute_approved_change(state: EngineeringState) -> EngineeringState:
    if state.get("approval_status") != "approved":
        return {
            **state,
            "status": "rejected",
            "change_result": {"error": "Change was not approved."},
        }

    plan = state.get("change_plan", {})
    path = str(plan.get("path", ""))
    if not path or path.startswith("/") or ".." in path.split("/"):
        return {
            **state,
            "status": "change_failed",
            "change_result": {"error": "Invalid repository path."},
        }

    branch = f"ai-fix-{uuid4().hex[:8]}"
    repository = state["repository"]
    base = state.get("ref", "main")
    agent = "code_agent"
    try:
        decision = DEFAULT_TOOL_POLICY.enforce(agent, "create_branch")
        branch_result = call_github_tool_sync(
            "create_branch",
            {"repository": repository, "branch": branch, "base_ref": base},
            agent=agent,
        )
        current_decision = DEFAULT_TOOL_POLICY.enforce(agent, "read_file")
        current = call_github_tool_sync(
            "read_file", {"repository": repository, "path": path, "ref": base}, agent=agent
        )
        current_data = json.loads(current)
        current_sha = current_data.get("sha")
        if not current_sha:
            raise ValueError("Unable to resolve current file SHA.")

        update_decision = DEFAULT_TOOL_POLICY.enforce(agent, "update_file")
        update_raw = call_github_tool_sync("update_file", {
            "repository": repository,
            "path": path,
            "content": str(plan.get("content", "")),
            "branch": branch,
            "message": str(plan.get("commit_message", "feat: apply approved engineering change")),
            "sha": current_sha,
        }, agent=agent)
        pr_decision = DEFAULT_TOOL_POLICY.enforce(agent, "create_pull_request")
        pr_raw = call_github_tool_sync("create_pull_request", {
            "repository": repository,
            "title": str(plan.get("pr_title", "feat: apply approved engineering change")),
            "body": str(plan.get("pr_body", "")),
            "head": branch,
            "base": base,
        }, agent=agent)
    except ToolPermissionError as exc:
        audited = _tool_audit(state, agent, exc.decision.tool, False, exc.decision.risk, "blocked")
        return {
            **audited,
            "status": "change_failed",
            "change_branch": branch,
            "change_result": {"error": str(exc)},
        }
    except (ValueError, KeyError, RuntimeError) as exc:
        return {
            **state,
            "status": "change_failed",
            "change_branch": branch,
            "change_result": {"error": str(exc), "branch_result": locals().get("branch_result")},
        }

    audited = state
    for tool, risk in (
        ("create_branch", decision.risk),
        ("read_file", current_decision.risk),
        ("update_file", update_decision.risk),
        ("create_pull_request", pr_decision.risk),
    ):
        audited = _tool_audit(audited, agent, tool, True, risk, "success")

    return {
        **audited,
        "status": "change_applied",
        "change_branch": branch,
        "change_result": json.loads(update_raw),
        "pull_request": json.loads(pr_raw),
    }


def verify_change(state: EngineeringState) -> EngineeringState:
    """Evaluate GitHub Actions check runs for the generated change commit."""
    pull_request = state.get("pull_request", {})
    head_sha = pull_request.get("head_sha")
    if not head_sha:
        return {
            **state,
            "status": "verification_failed",
            "verification_status": "failed",
            "verification_result": {"error": "Pull request head SHA is unavailable."},
        }

    agent = "verification_agent"
    try:
        decision = DEFAULT_TOOL_POLICY.enforce(agent, "get_commit_checks")
        raw = call_github_tool_sync(
            "get_commit_checks",
            {"repository": state["repository"], "ref": head_sha},
            agent=agent,
        )
    except ToolPermissionError as exc:
        audited = _tool_audit(state, agent, exc.decision.tool, False, exc.decision.risk, "blocked")
        return {
            **audited,
            "status": "verification_failed",
            "verification_status": "failed",
            "verification_result": {"error": str(exc)},
        }
    try:
        data = json.loads(raw)
    except (TypeError, ValueError) as exc:
        return {
            **state,
            "status": "verification_failed",
            "verification_status": "failed",
            "verification_result": {"error": str(exc)},
        }

    audited = _tool_audit(state, agent, "get_commit_checks", True, decision.risk, "success")
    checks = data.get("checks", [])
    if not checks:
        return {
            **audited,
            "status": "verification_pending",
            "verification_status": "pending",
            "verification_result": {
                "message": "CI has not reported any check runs yet.",
                "checks": [],
            },
        }

    pending = [item for item in checks if item.get("status") != "completed"]
    failed = [
        item for item in checks
        if item.get("status") == "completed"
        and item.get("conclusion") not in {"success", "skipped", "neutral"}
    ]
    if pending:
        verification_status = "pending"
        status = "verification_pending"
    elif failed:
        verification_status = "failed"
        status = "verification_failed"
    else:
        verification_status = "passed"
        status = "verification_passed"

    return {
        **audited,
        "status": status,
        "verification_status": verification_status,
        "verification_result": {
            "checks": checks,
            "passed": verification_status == "passed",
            "failed_checks": failed,
        },
    }
