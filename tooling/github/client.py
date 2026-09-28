import os
from typing import Any

import httpx


class GitHubClient:
    def __init__(self) -> None:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN is required for GitHub MCP tools.")
        self.token = token

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = httpx.request(
            method,
            f"https://api.github.com{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Authorization": f"Bearer {self.token}",
            },
            timeout=20.0,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def read_file(self, repository: str, path: str, ref: str = "main") -> Any:
        return self._get(f"/repos/{repository}/contents/{path}", {"ref": ref})

    def search_code(self, repository: str, query: str) -> Any:
        return self._get("/search/code", {"q": f"{query} repo:{repository}", "per_page": "20"})

    def list_repository(self, repository: str, path: str = "", ref: str = "main") -> Any:
        endpoint = f"/repos/{repository}/contents/{path}".rstrip("/")
        return self._get(endpoint, {"ref": ref})

    def create_branch(self, repository: str, branch: str, base_ref: str = "main") -> Any:
        base = self._get(f"/repos/{repository}/git/ref/heads/{base_ref}")
        return self._request(
            "POST",
            f"/repos/{repository}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": base["object"]["sha"]},
        )

    def update_file(
        self,
        repository: str,
        path: str,
        content: str,
        branch: str,
        message: str,
        sha: str,
    ) -> Any:
        import base64

        return self._request(
            "PUT",
            f"/repos/{repository}/contents/{path}",
            json={
                "message": message,
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "branch": branch,
                "sha": sha,
            },
        )

    def create_pull_request(
        self,
        repository: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> Any:
        return self._request(
            "POST",
            f"/repos/{repository}/pulls",
            json={"title": title, "body": body, "head": head, "base": base},
        )

    def get_commit_checks(self, repository: str, ref: str) -> Any:
        return self._get(
            f"/repos/{repository}/commits/{ref}/check-runs",
            {"per_page": "50"},
        )
