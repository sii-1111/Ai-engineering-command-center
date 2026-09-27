import os
from typing import Any

import httpx


class GitHubClient:
    def __init__(self) -> None:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN is required for GitHub MCP tools.")
        self.token = token

    def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        response = httpx.get(
            f"https://api.github.com{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Authorization": f"Bearer {self.token}",
            },
            params=params,
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()

    def read_file(self, repository: str, path: str, ref: str = "main") -> Any:
        return self._get(f"/repos/{repository}/contents/{path}", {"ref": ref})

    def search_code(self, repository: str, query: str) -> Any:
        return self._get("/search/code", {"q": f"{query} repo:{repository}", "per_page": "20"})

    def list_repository(self, repository: str, path: str = "", ref: str = "main") -> Any:
        endpoint = f"/repos/{repository}/contents/{path}".rstrip("/")
        return self._get(endpoint, {"ref": ref})
