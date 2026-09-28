from agents import tool_executor
from agents.llm_planner import LLM
from core.graph import build_graph


class FakeLLM:
    def invoke_json(self, messages: list[dict[str, str]]) -> dict:
        return {
            "steps": [
                {
                    "tool": "search_code",
                    "arguments": {"query": "Find the search implementation."},
                },
                {
                    "tool": "list_repository",
                    "arguments": {"path": ""},
                },
            ]
        }


def fake_github_tool(tool_name: str, arguments: dict) -> str:
    if tool_name == "search_code":
        return '{"query":"Find the search implementation.","matches":[{"path":"apps/api/app/main.py","sha":"abc"}]}'
    if tool_name == "list_repository":
        return '[{"name":"apps","path":"apps","type":"dir"},{"name":"README.md","path":"README.md","type":"file"}]'
    raise AssertionError(f"Unexpected tool: {tool_name}")


def test_graph_runs_github_investigation(monkeypatch) -> None:
    monkeypatch.setattr("agents.llm_planner.LLM", FakeLLM)
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
    assert len(result["dynamic_plan"]) == 2
    assert len(result["tool_calls"]) == 2
    assert len(result["evidence"]) == 2
    assert result["tool_calls"][0]["tool"] == "github.search_code"
    assert result["tool_calls"][1]["tool"] == "github.list_repository"


def test_graph_requires_repository(monkeypatch) -> None:
    monkeypatch.setattr("agents.llm_planner.LLM", FakeLLM)
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
