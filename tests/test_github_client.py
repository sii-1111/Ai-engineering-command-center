from unittest.mock import Mock, patch

import httpx
import pytest

from tooling.github.client import GitHubClient


@patch("tooling.github.client.httpx.request")
def test_public_repository_reads_work_without_github_token(request, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    response = Mock()
    response.json.return_value = {"name": "README.md"}
    request.return_value = response

    result = GitHubClient().read_file("owner/repository", "README.md")

    assert result == {"name": "README.md"}
    assert "Authorization" not in request.call_args.kwargs["headers"]


@patch("tooling.github.client.httpx.request")
def test_github_writes_still_require_a_token(request, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="GITHUB_TOKEN is required"):
        GitHubClient().create_branch("owner/repository", "feature/demo")

    request.assert_not_called()


@patch("tooling.github.client.httpx.request")
def test_rejected_token_retries_public_read_without_authorization(request, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "invalid-test-token")
    url = "https://api.github.com/repos/owner/repository/contents/README"
    request.side_effect = [
        httpx.Response(401, json={"message": "Bad credentials"}, request=httpx.Request("GET", url)),
        httpx.Response(200, json={"name": "README"}, request=httpx.Request("GET", url)),
    ]

    result = GitHubClient().read_file("owner/repository", "README")

    assert result == {"name": "README"}
    assert "Authorization" in request.call_args_list[0].kwargs["headers"]
    assert "Authorization" not in request.call_args_list[1].kwargs["headers"]


@patch("tooling.github.client.httpx.request")
def test_code_search_without_token_returns_public_read_guidance(request, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    result = GitHubClient().search_code("owner/repository", "README")

    assert result["items"] == []
    assert "list_repository and read_file" in result["warning"]
    request.assert_not_called()