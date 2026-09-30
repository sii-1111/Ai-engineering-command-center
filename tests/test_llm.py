from unittest.mock import Mock, patch

from openai import InternalServerError

from core.llm import GEMINI_API_BASE_URL, LLM, llm_configuration_error


def test_gemini_is_default_provider_and_uses_environment_key(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")

    with patch("core.llm.OpenAI") as openai_client:
        llm = LLM()

    openai_client.assert_called_once_with(
        api_key="test-key",
        base_url=GEMINI_API_BASE_URL,
    )
    assert llm.deployment == "gemini-test-model"


def test_gemini_provider_reports_missing_api_key(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    assert llm_configuration_error() == "Set backend environment variables: GEMINI_API_KEY"



def test_gemini_uses_fallback_model_after_temporary_unavailability(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-primary")
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "gemini-fallback-1, gemini-fallback-2")
    response = Mock(choices=[Mock(message=Mock(content="ok"))])

    with patch("core.llm.OpenAI") as openai_client:
        request = openai_client.return_value.chat.completions.create
        request.side_effect = [
            InternalServerError("temporarily unavailable", response=Mock(status_code=503), body={}),
            InternalServerError("temporarily unavailable", response=Mock(status_code=503), body={}),
            response,
        ]
        result = LLM().invoke([{"role": "user", "content": "hello"}])

    assert result == "ok"
    assert request.call_count == 3
    assert request.call_args_list[0].kwargs["model"] == "gemini-primary"
    assert request.call_args_list[1].kwargs["model"] == "gemini-fallback-1"
    assert request.call_args_list[2].kwargs["model"] == "gemini-fallback-2"