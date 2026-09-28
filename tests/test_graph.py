from agents import llm_planner, tool_executor
from core.graph import build_graph


class FakeLLM:
    calls = 0

    def invoke_json(self, messages: list[dict[str, str]]) -> dict:
        FakeLLM.calls += 1
        if FakeLLM.calls == 1:
            return {
                "tool": "search_code",
                "arguments": {"query": "Find the search implementation."},
            }
        return {
            "action": "finish",
            "report": {
                "root_cause": "Search implementation was identified in the evidence.",
                "evidence": ["apps/api/app/main.py contains the endpoint."],
                "impact": "The endpoint is the relevant investigation target.",
                "recommended_change": "Inspect and optimize the identified implementation.",
                "files_involved": ["apps/api/app/main.py"],
                "confidence": 0.9,
                "approval_required": False,
            },
        }


def fake_github_tool(tool_name: str, arguments: dict) -> str:
    if tool_name == "search_code":
        return '{"query":"Find the search implementation.","matches":[{"path":"apps/api/app/main.py","sha":"abc"}]}'
    raise AssertionError(f"Unexpected tool: {tool_name}")


def test_graph_runs_bounded_iterative_investigation(monkeypatch) -> None:
    FakeLLM.calls = 0
    monkeypatch.setattr(llm_planner, "LLM", FakeLLM)
    monkeypatch.setattr(tool_executor, "call_github_tool_sync", fake_github_tool)

    result = build_graph().invoke({
        "task": "Find the search implementation.",
        "repository": "sii-1111/Ai-engineering-command-center",
        "ref": "main",
        "evidence": [],
        "findings": [],
        "tool_calls": [],
        "status": "started",
    })

    assert result["status"] == "completed"
    assert len(result["tool_calls"]) == 1
    assert len(result["evidence"]) == 1
    assert result["tool_calls"][0]["tool"] == "github.search_code"
    assert result["report"]["confidence"] == 0.9
    assert "Root Cause:" in result["final_report"]
    assert FakeLLM.calls == 2


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
        })
    except KeyError as exc:
        assert str(exc).strip("'") == "repository"
    else:
        raise AssertionError("Expected repository to be required by the graph")
