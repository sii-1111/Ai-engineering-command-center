from core.graph import build_graph


def test_graph_produces_plan_and_report() -> None:
    result = build_graph().invoke({
        "task": "Find why the search endpoint is slow.",
        "evidence": [],
        "findings": [],
        "tool_calls": [],
        "status": "started",
    })

    assert result["status"] == "completed"
    assert len(result["plan"]) == 4
    assert "Task:" in result["final_report"]
