import pytest

from core.security.tool_policy import DEFAULT_TOOL_POLICY, ToolPermissionError


def test_research_agent_is_read_only():
    assert DEFAULT_TOOL_POLICY.authorize("research_agent", "read_file").allowed
    assert DEFAULT_TOOL_POLICY.authorize("research_agent", "search_code").allowed
    assert not DEFAULT_TOOL_POLICY.authorize("research_agent", "update_file").allowed


def test_code_agent_can_mutate_only_through_approved_tools():
    for tool in ("create_branch", "update_file", "create_pull_request"):
        assert DEFAULT_TOOL_POLICY.authorize("code_agent", tool).allowed
    assert not DEFAULT_TOOL_POLICY.authorize("code_agent", "search_code").allowed


def test_reviewer_and_verification_permissions_are_restricted():
    assert DEFAULT_TOOL_POLICY.authorize("reviewer_agent", "read_file").allowed
    assert not DEFAULT_TOOL_POLICY.authorize("reviewer_agent", "update_file").allowed
    assert DEFAULT_TOOL_POLICY.authorize("verification_agent", "get_commit_checks").allowed
    assert not DEFAULT_TOOL_POLICY.authorize("verification_agent", "create_pull_request").allowed


def test_unknown_tools_are_critical_and_blocked():
    decision = DEFAULT_TOOL_POLICY.authorize("code_agent", "shell_exec")
    assert not decision.allowed
    assert decision.risk == "critical"


def test_enforce_raises_with_structured_denial():
    with pytest.raises(ToolPermissionError) as exc_info:
        DEFAULT_TOOL_POLICY.enforce("research_agent", "update_file")
    assert exc_info.value.decision.as_dict() == {
        "allowed": False,
        "agent": "research_agent",
        "tool": "update_file",
        "risk": "high",
        "reason": "Agent 'research_agent' is not permitted to execute 'update_file'.",
    }
