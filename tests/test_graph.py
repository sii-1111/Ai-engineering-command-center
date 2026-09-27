from agents import github_investigator
from core.graph import build_graph


def fake_github_tool(tool_name: str, arguments: dict) -> str:
    if tool_name == "search_code":
        return '{"query":"test task","matches":[{"path":"apps/api/app/main.py","sha":"abc"}]}'
    if tool_name == "list_repository":
        return '[{"name":"apps","path":"apps","type":"dir"},{"name":"README.md","path":"README.md","type":"file"}]'
    raise AssertionError(f"Unexpected tool: {tool_name}")


def test_graph_runs_github_investigation(monkeypatch) -> None:
    monkeypatch.setattr(github_investigator, "call_github_tool_sync", fake_github_tool)

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
    assert result["findings"] == [
        "GitHub code search returned 1 matching file(s): ['apps/api/app/main.py']"
    ]
    assert len(result["tool_calls"]) == 2
    assert len(result["evidence"]) == 3


def test_graph_requires_repository(monkeypatch) -> None:
    # The API validates repository input; the graph itself expects it at runtime.
    monkeypatch.setattr(github_investigator, "call_github_tool_sync", fake_github_tool)
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
