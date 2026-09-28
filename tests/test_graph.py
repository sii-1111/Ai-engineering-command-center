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
        return '{"number":99,"html_url":"https://github.com/example/repo/pull/99"}'
    raise AssertionError(f"Unexpected tool: {tool_name}")


def _config() -> dict:
    return {"configurable": {"thread_id": str(uuid4())}}


def test_graph_pauses_for_human_approval(monkeypatch) -> None:
    FakeLLM.calls = 0
    monkeypatch.setattr(llm_planner, "LLM", FakeLLM)
    monkeypatch.setattr(tool_executor, "call_github_tool_sync", fake_github_tool)

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

    assert resumed["status"] == "change_applied"
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
