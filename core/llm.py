import os
from typing import Any

from openai import AzureOpenAI


class LLM:
    def __init__(self) -> None:
        self.client = AzureOpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )
        self.deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]

    def invoke(self, messages: list[dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=0,
        )
        return response.choices[0].message.content or ""

    def invoke_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        import json
        return json.loads(response.choices[0].message.content or "{}")
