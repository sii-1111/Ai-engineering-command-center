import pytest

from core.security.access import Principal, authenticate_token, authorize_task, authorize_tool
from core.security.audit import audit_event


def test_viewer_cannot_create_tasks():
    principal = Principal("u1", frozenset({"viewer"}))
    with pytest.raises(PermissionError):
        authorize_task(principal, "task:create")


def test_engineer_can_create_and_approve():
    principal = Principal("u1", frozenset({"engineer"}))
    authorize_task(principal, "task:create")
    authorize_task(principal, "task:approve")


def test_high_risk_tool_requires_approval_permission():
    principal = Principal("u1", frozenset({"engineer"}))
    decision = authorize_tool(principal, "code_agent", "update_file")
    assert decision.allowed is True


def test_authentication_uses_configured_token(monkeypatch):
    monkeypatch.setenv("COMMAND_CENTER_API_TOKEN", "test-token")
    monkeypatch.setenv("COMMAND_CENTER_API_ROLE", "viewer")
    principal = authenticate_token("test-token")
    assert principal is not None
    assert principal.roles == frozenset({"viewer"})
    assert authenticate_token("wrong") is None


def test_audit_redacts_secrets():
    event = audit_event(
        subject="u1",
        action="task.create",
        resource="task-1",
        outcome="success",
        metadata={"token": "secret", "repository": "org/repo"},
    )
    assert "token" not in event["metadata"]
    assert event["metadata"]["repository"] == "org/repo"
