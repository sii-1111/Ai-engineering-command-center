from unittest.mock import Mock

from fastapi.testclient import TestClient
from apps.api.app.main import _serialize_result, app


def test_create_task_reports_missing_gemini_key(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = TestClient(app).post(
        "/v1/tasks",
        json={
            "task": "Inspect the repository",
            "repository": "owner/repository",
            "ref": "main",
        },
    )

    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


def test_create_task_queues_provider_work_without_blocking(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("apps.api.app.main.task_store.save", Mock(return_value=True))
    monkeypatch.setattr("apps.api.app.main.audit_event", Mock(return_value={"event": "queued"}))
    monkeypatch.setattr("apps.api.app.main.graph.invoke", Mock(return_value={"status": "completed"}))

    response = TestClient(app).post(
        "/v1/tasks",
        json={
            "task": "Inspect the repository",
            "repository": "owner/repository",
            "ref": "main",
        },
        headers={"Origin": "http://localhost:3003"},
    )

    assert response.status_code == 202
    assert response.headers["access-control-allow-origin"] == "*"
    assert response.json()["status"] == "queued"
    assert response.json()["task_id"]


def test_serialize_result_includes_raw_evidence_and_tool_calls() -> None:
    result = _serialize_result(
        "task-id",
        {
            "status": "completed",
            "evidence": [{"source": "github://owner/repository/read_file", "detail": "README text"}],
            "tool_calls": [{"tool": "github.read_file", "status": "success"}],
        },
    )

    assert result["evidence"][0]["detail"] == "README text"
    assert result["tool_calls"][0]["tool"] == "github.read_file"