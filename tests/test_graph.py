from uuid import uuid4

from langgraph.types import Command

from agents import llm_planner, tool_executor
from core.graph import build_graph

SEARCH_EVIDENCE = (
    '{"query":"Find the search implementation.",'
    '"matches":[{"path":"apps/api/app/main.py","sha":"abc"}]}'
)


class FakeLLM:
    calls = 0

    def invoke_json(self, messages: list[dict[str, str]]) -> dict:
        FakeLLM.calls += 1
        if FakeLLM.calls == 1:
            return {
                "tool": "search_code",
                "arguments": {"query": "Find the search implementation."},
            }
        if FakeLLM.calls == 2:
            return {
                "action": "finish",
                "report": {
                    "root_cause": "The search endpoint is implemented in the identified file.",
                    "evidence": [SEARCH_EVIDENCE],
                    "impact": "The identified endpoint is the relevant investigation target.",
                    "recommended_change": "Inspect and optimize the identified implementation.",
                    "files_involved": ["apps/api/app/main.py"],
                    "confidence": 0.9,
                    "approval_required": True,
                },
            }
        return {
            "path": "apps/api/app/main.py",
            "content": "fixed = True\\n",
            "summary": "Apply the approved optimization.",
            "commit_message": "fix: optimize search endpoint",
            "pr_title": "fix: optimize search endpoint",
            "pr_body": "Applies the approved engineering change.",
        }


def fake_github_tool(tool_name: str, arguments: dict) -> str:
    if tool_name == "search_code":
        return SEARCH_EVIDENCE
    if tool_name == "create_branch":
        return '{"ref":"refs/heads/ai-fix-test"}'
    if tool_name == "read_file":
        return '{"path":"apps/api/app/main.py","sha":"current-sha"}'
    if tool_name == "update_file":
        return '{"commit":{"sha":"change-commit"}}'
    if tool_name == "create_pull_request":
        return '{"number":99,"html_url":"https://github.com/example/repo/pull/99","head_sha":"test-head-sha"}'
    if tool_name == "get_commit_checks":
        return '{"ref":"test-head-sha","total_count":1,"checks":[{"name":"Tests","status":"completed","conclusion":"success","url":"https://github.com/example/check"}]}'
    raise AssertionError(f"Unexpected tool: {tool_name}")


def _config() -> dict:
    return {"configurable": {"thread_id": str(uuid4())}}


def test_graph_pauses_for_human_approval(monkeypatch) -> None:
    FakeLLM.calls = 0
    monkeypatch.setattr(llm_planner, "LLM", FakeLLM)
    monkeypatch.setattr(tool_executor, "call_github_tool_sync", fake_github_tool)
    monkeypatch.setattr("agents.reviewer.LLM", FakeLLM)

    graph = build_graph()
    result = graph.invoke({
        "task": "Find the search implementation.",
        "repository": "sii-1111/Ai-engineering-command-center",
        "ref": "main",
        "evidence": [],
        "findings": [],
        "tool_calls": [],
        "status": "started",
    }, config=_config())

    assert result["status"] == "awaiting_approval"
    assert result["report"]["confidence"] == 0.9
    assert result["report"]["approval_required"] is True
    assert result["__interrupt__"][0].value["type"] == "approval_required"
    assert result["__interrupt__"][0].value["report"]["confidence"] == 0.9
    assert FakeLLM.calls == 3


def test_graph_resumes_after_approval(monkeypatch) -> None:
    FakeLLM.calls = 0
    monkeypatch.setattr(llm_planner, "LLM", FakeLLM)
    monkeypatch.setattr(tool_executor, "call_github_tool_sync", fake_github_tool)

    graph = build_graph()
    config = _config()
    paused = graph.invoke({
        "task": "Find the search implementation.",
        "repository": "sii-1111/Ai-engineering-command-center",
        "ref": "main",
        "evidence": [],
        "findings": [],
        "tool_calls": [],
        "status": "started",
    }, config=config)

    assert paused["__interrupt__"]
    resumed = graph.invoke(Command(resume=True), config=config)

    assert resumed["status"] == "verification_passed"
    assert resumed["approval_status"] == "approved"
    assert resumed["report"]["approval_required"] is True
    assert resumed["change_branch"].startswith("ai-fix-")
    assert "__interrupt__" not in resumed


def test_graph_stops_after_rejection(monkeypatch) -> None:
    FakeLLM.calls = 0
    monkeypatch.setattr(llm_planner, "LLM", FakeLLM)
    monkeypatch.setattr(tool_executor, "call_github_tool_sync", fake_github_tool)

    graph = build_graph()
    config = _config()
    graph.invoke({
        "task": "Find the search implementation.",
        "repository": "sii-1111/Ai-engineering-command-center",
        "ref": "main",
        "evidence": [],
        "findings": [],
        "tool_calls": [],
        "status": "started",
    }, config=config)

    rejected = graph.invoke(Command(resume=False), config=config)

    assert rejected["status"] == "rejected"
    assert rejected["approval_status"] == "rejected"


def test_report_rejects_unsupported_evidence_and_clamps_confidence(monkeypatch) -> None:
    FakeLLM.calls = 0

    class UnsafeFakeLLM(FakeLLM):
        def invoke_json(self, messages: list[dict[str, str]]) -> dict:
            UnsafeFakeLLM.calls += 1
            if UnsafeFakeLLM.calls == 1:
                return {
                    "tool": "search_code",
                    "arguments": {"query": "Find the search implementation."},
                }
            return {
                "action": "finish",
                "report": {
                    "root_cause": "Unsupported claim",
                    "evidence": ["made-up evidence"],
                    "impact": "Unknown",
                    "recommended_change": "None",
                    "files_involved": [],
                    "confidence": 4.2,
                    "approval_required": False,
                },
            }

    monkeypatch.setattr(llm_planner, "LLM", UnsafeFakeLLM)
    monkeypatch.setattr(tool_executor, "call_github_tool_sync", fake_github_tool)
    result = build_graph().invoke({
        "task": "Find the search implementation.",
        "repository": "sii-1111/Ai-engineering-command-center",
        "ref": "main",
        "evidence": [],
        "findings": [],
        "tool_calls": [],
        "status": "started",
    }, config=_config())

    assert result["report"]["evidence"] == []
    assert result["report"]["confidence"] == 1.0


def test_graph_requires_repository(monkeypatch) -> None:
    FakeLLM.calls = 0
    monkeypatch.setattr(llm_planner, "LLM", FakeLLM)
    monkeypatch.setattr(tool_executor, "call_github_tool_sync", fake_github_tool)
    try:
        build_graph().invoke({
            "task": "Find the search implementation.",
            "evidence": [],
            "findings": [],
            "tool_calls": [],
            "status": "started",
        }, config=_config())
    except KeyError as exc:
        assert str(exc).strip("'") == "repository"
    else:
        raise AssertionError("Expected repository to be required by the graph")


def test_approved_change_creates_branch_updates_file_and_opens_pr(monkeypatch) -> None:
    calls = []

    def fake_write_tool(tool_name: str, arguments: dict) -> str:
        calls.append((tool_name, arguments))
        if tool_name == "read_file":
            return '{"path":"apps/api/app/main.py","sha":"current-sha"}'
        if tool_name == "create_branch":
            return '{"ref":"refs/heads/ai-fix-test"}'
        if tool_name == "update_file":
            return '{"commit":{"sha":"change-commit"}}'
        if tool_name == "create_pull_request":
            return '{"number":99,"html_url":"https://github.com/example/repo/pull/99"}'
        raise AssertionError(tool_name)

    monkeypatch.setattr("agents.tool_executor.call_github_tool_sync", fake_write_tool)
    from agents.tool_executor import execute_approved_change

    result = execute_approved_change({
        "repository": "sii-1111/Ai-engineering-command-center",
        "ref": "main",
        "approval_status": "approved",
        "change_plan": {
            "path": "apps/api/app/main.py",
            "content": "fixed = True\n",
            "commit_message": "fix: optimize search endpoint",
            "pr_title": "fix: optimize search endpoint",
            "pr_body": "Applies the approved engineering change.",
        },
    })

    assert result["status"] == "change_applied"
    assert result["pull_request"]["number"] == 99
    assert [item[0] for item in calls] == [
        "create_branch", "read_file", "update_file", "create_pull_request"
    ]
    assert calls[2][1]["sha"] == "current-sha"


def test_verify_change_passes_when_all_checks_succeed(monkeypatch) -> None:
    def fake_checks(tool_name: str, arguments: dict) -> str:
        assert tool_name == "get_commit_checks"
        assert arguments["ref"] == "head-sha"
        return (
            '{"ref":"head-sha","total_count":2,"checks":['
            '{"name":"Lint","status":"completed","conclusion":"success"},'
            '{"name":"Tests","status":"completed","conclusion":"success"}]}'
        )

    monkeypatch.setattr(tool_executor, "call_github_tool_sync", fake_checks)
    result = tool_executor.verify_change({
        "repository": "sii-1111/Ai-engineering-command-center",
        "pull_request": {"head_sha": "head-sha"},
    })
    assert result["status"] == "verification_passed"
    assert result["verification_status"] == "passed"
    assert result["verification_result"]["passed"] is True


def test_verify_change_stays_pending_while_checks_run(monkeypatch) -> None:
    def fake_checks(tool_name: str, arguments: dict) -> str:
        return (
            '{"ref":"head-sha","total_count":1,"checks":['
            '{"name":"Tests","status":"in_progress","conclusion":null}]}'
        )

    monkeypatch.setattr(tool_executor, "call_github_tool_sync", fake_checks)
    result = tool_executor.verify_change({
        "repository": "sii-1111/Ai-engineering-command-center",
        "pull_request": {"head_sha": "head-sha"},
    })
    assert result["status"] == "verification_pending"
    assert result["verification_status"] == "pending"


def test_verify_change_fails_when_a_check_fails(monkeypatch) -> None:
    def fake_checks(tool_name: str, arguments: dict) -> str:
        return (
            '{"ref":"head-sha","total_count":1,"checks":['
            '{"name":"Tests","status":"completed","conclusion":"failure"}]}'
        )

    monkeypatch.setattr(tool_executor, "call_github_tool_sync", fake_checks)
    result = tool_executor.verify_change({
        "repository": "sii-1111/Ai-engineering-command-center",
        "pull_request": {"head_sha": "head-sha"},
    })
    assert result["status"] == "verification_failed"
    assert result["verification_status"] == "failed"
    assert result["verification_result"]["failed_checks"][0]["name"] == "Tests"



def test_reviewer_approves_verified_change(monkeypatch) -> None:
    class ReviewLLM:
        def invoke_json(self, messages: list[dict[str, str]]) -> dict:
            return {
                "decision": "approve",
                "summary": "The change addresses the reported root cause and verification passed.",
                "findings": [],
                "confidence": 0.95,
            }

    monkeypatch.setattr("agents.reviewer.LLM", ReviewLLM)
    result = __import__("agents.reviewer", fromlist=["review_change"]).review_change({
        "task": "Optimize the search endpoint.",
        "report": {
            "root_cause": "Inefficient search implementation.",
            "evidence": ["observed evidence"],
            "impact": "High latency.",
            "recommended_change": "Optimize the search implementation.",
            "files_involved": ["apps/api/app/main.py"],
            "confidence": 0.9,
            "approval_required": True,
        },
        "evidence": [{"source": "github://repo/read_file", "detail": "observed evidence"}],
        "change_plan": {"path": "apps/api/app/main.py", "summary": "Optimize search."},
        "verification_status": "passed",
        "verification_result": {"passed": True, "checks": []},
    })
    assert result["status"] == "review_approve"
    assert result["review"]["decision"] == "approve"
    assert result["review"]["findings"] == []


def test_reviewer_normalizes_unsafe_decision_and_confidence(monkeypatch) -> None:
    class ReviewLLM:
        def invoke_json(self, messages: list[dict[str, str]]) -> dict:
            return {
                "decision": "unknown",
                "summary": "Needs review.",
                "findings": [{"severity": "urgent", "category": "safety", "message": "Check manually."}],
                "confidence": 4.0,
            }

    monkeypatch.setattr("agents.reviewer.LLM", ReviewLLM)
    from agents.reviewer import review_change

    result = review_change({"task": "Review change.", "verification_status": "failed"})
    assert result["review"]["decision"] == "request_changes"
    assert result["review"]["findings"][0]["severity"] == "medium"
    assert result["review"]["confidence"] == 1.0
