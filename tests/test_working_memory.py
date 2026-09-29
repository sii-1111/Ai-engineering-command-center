from core.memory.working import WorkingMemory, memory_to_state


def test_working_memory_is_bounded_and_serializable():
    memory = WorkingMemory("task-1")
    for i in range(45):
        memory.add_evidence(f"file-{i}", f"evidence-{i}")
    for i in range(45):
        memory.add_tool_call("read_file", {"path": f"{i}.py"})
    for i in range(25):
        memory.add_decision(f"decision-{i}")

    state = memory_to_state(memory)

    assert len(state["evidence"]) == 40
    assert len(state["tool_calls"]) == 40
    assert len(state["memory_decisions"]) == 20
    assert state["evidence"][0]["source"] == "file-5"


def test_working_memory_restores_from_graph_state():
    memory = WorkingMemory.from_state(
        "task-2",
        {
            "memory_summary": "investigating",
            "evidence": [{"source": "a.py", "detail": "query"}],
            "tool_calls": [{"tool": "read_file"}],
            "memory_decisions": [{"decision": "next:search_code"}],
        },
    )

    assert memory.summary == "investigating"
    assert memory.evidence[0]["source"] == "a.py"
    assert memory.tool_calls[0]["tool"] == "read_file"
    assert memory.decisions[0]["decision"] == "next:search_code"
