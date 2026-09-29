from unittest.mock import patch

from agents.tool_executor import execute_next_tool


@patch("agents.tool_executor.call_github_tool_sync")
@patch("agents.tool_executor.search_repository")
def test_execute_next_tool_routes_rag_without_mcp(rag_search, github_call):
    rag_search.return_value = [
        {
            "source": "app.py",
            "content": "slow database query",
            "score": 3.4,
            "repository": "owner/repo",
            "ref": "main",
        }
    ]
    state = {
        "task": "find the slow database query",
        "repository": "owner/repo",
        "ref": "main",
        "dynamic_plan": [{
            "tool": "search_repository_rag",
            "arguments": {"query": "slow database query", "top_k": 3},
        }],
        "evidence": [],
        "tool_calls": [],
        "observability_events": [],
    }

    result = execute_next_tool(state)

    rag_search.assert_called_once_with(
        "slow database query",
        repository="owner/repo",
        ref="main",
        top_k=3,
    )
    github_call.assert_not_called()
    assert result["status"] == "evidence_ready"
    assert result["tool_calls"][0]["tool"] == "repository.rag"
