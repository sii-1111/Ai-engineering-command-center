import base64
import json

from mcp.server.fastmcp import FastMCP

from tooling.github.client import GitHubClient

mcp = FastMCP("github-engineering-tools")


def client() -> GitHubClient:
    return GitHubClient()


@mcp.tool()
def read_file(repository: str, path: str, ref: str = "main") -> str:
    """Read a text file from a GitHub repository."""
    result = client().read_file(repository, path, ref)
    content = result.get("content", "")
    if result.get("encoding") == "base64":
        content = base64.b64decode(content).decode("utf-8", errors="replace")
    return json.dumps({
        "path": path,
        "sha": result.get("sha"),
        "content": content,
        "url": result.get("html_url"),
    })


@mcp.tool()
def search_code(repository: str, query: str) -> str:
    """Search GitHub code within one repository."""
    result = client().search_code(repository, query)
    return json.dumps({
        "query": query,
        "matches": [
            {"path": item.get("path"), "sha": item.get("sha"), "url": item.get("html_url")}
            for item in result.get("items", [])
        ],
    })


@mcp.tool()
def list_repository(repository: str, path: str = "", ref: str = "main") -> str:
    """List files or directories at a repository path."""
    result = client().list_repository(repository, path, ref)
    return json.dumps([
        {"name": x.get("name"), "path": x.get("path"), "type": x.get("type")}
        for x in result
    ])


@mcp.tool()
def create_branch(repository: str, branch: str, base_ref: str = "main") -> str:
    """Create a new branch from a base ref. Use only after human approval."""
    return json.dumps(client().create_branch(repository, branch, base_ref))


@mcp.tool()
def update_file(
    repository: str,
    path: str,
    content: str,
    branch: str,
    message: str,
    sha: str,
) -> str:
    """Update an existing file on an already-created branch. Use only after human approval."""
    return json.dumps(client().update_file(repository, path, content, branch, message, sha))


@mcp.tool()
def create_pull_request(
    repository: str,
    title: str,
    body: str,
    head: str,
    base: str = "main",
) -> str:
    """Create a pull request from a change branch to the base branch."""
    return json.dumps(client().create_pull_request(repository, title, body, head, base))


@mcp.tool()
def get_commit_checks(repository: str, ref: str) -> str:
    """Read CI check-run status for a commit or branch."""
    result = client().get_commit_checks(repository, ref)
    return json.dumps({
        "ref": ref,
        "total_count": result.get("total_count", 0),
        "checks": [
            {
                "name": item.get("name"),
                "status": item.get("status"),
                "conclusion": item.get("conclusion"),
                "url": item.get("html_url"),
            }
            for item in result.get("check_runs", [])
        ],
    })


if __name__ == "__main__":
    mcp.run()
