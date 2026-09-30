import json
import os
from typing import Any

from openai import APIStatusError, AzureOpenAI, OpenAI

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def selected_provider() -> str:
    configured = os.getenv("LLM_PROVIDER", "").strip().lower()
    if configured:
        return configured
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if any(os.getenv(name) for name in ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT")):
        return "azure"
    return "gemini"


def llm_configuration_error() -> str | None:
    provider = selected_provider()
    if provider == "gemini":
        missing = [name for name in ("GEMINI_API_KEY",) if not os.getenv(name)]
    elif provider == "azure":
        required = ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT")
        missing = [name for name in required if not os.getenv(name)]
    else:
        return "LLM_PROVIDER must be 'gemini' or 'azure'."
    if missing:
        return f"Set backend environment variables: {', '.join(missing)}"
    return None


class LLM:
    def __init__(self) -> None:
        configuration_error = llm_configuration_error()
        if configuration_error:
            raise ValueError(configuration_error)

        provider = selected_provider()
        self.provider = provider
        if provider == "gemini":
            self.client = OpenAI(
                api_key=os.environ["GEMINI_API_KEY"],
                base_url=os.getenv("GEMINI_API_BASE_URL", GEMINI_API_BASE_URL),
            )
            self.deployment = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        else:
            self.client = AzureOpenAI(
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            )
            self.deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]

    def invoke(self, messages: list[dict[str, str]]) -> str:
        response = self._create_completion(messages)
        return response.choices[0].message.content or ""

    def invoke_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        response = self._create_completion(messages, json_mode=True)
        return json.loads(response.choices[0].message.content or "{}")

    def _create_completion(self, messages: list[dict[str, str]], *, json_mode: bool = False) -> Any:
        request = {
            "model": self.deployment,
            "messages": messages,
            "temperature": 0,
        }
        if json_mode:
            request["response_format"] = {"type": "json_object"}
        try:
            return self.client.chat.completions.create(**request)
        except APIStatusError as exc:
            if self.provider != "gemini" or exc.status_code not in {429, 503}:
                raise
            fallback_models = os.getenv(
                "GEMINI_FALLBACK_MODELS",
                "gemini-3.7-flash,gemini-3.5-flash-lite",
            )
            attempted_models = {self.deployment}
            last_error = exc
            for fallback_model in fallback_models.split(","):
                fallback_model = fallback_model.strip()
                if not fallback_model or fallback_model in attempted_models:
                    continue
                attempted_models.add(fallback_model)
                request["model"] = fallback_model
                try:
                    return self.client.chat.completions.create(**request)
                except APIStatusError as fallback_error:
                    if fallback_error.status_code not in {429, 503}:
                        raise
                    last_error = fallback_error
            raise last_error
