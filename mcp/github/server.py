import base64
import json
from mcp.server.fastmcp import FastMCP
from mcp.github.client import GitHubClient

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
    return json.dumps({"path": path, "sha": result.get("sha"), "content": content, "url": result.get("html_url")})


@mcp.tool()
def search_code(repository: str, query: str) -> str:
    """Search GitHub code within one repository."""
    result = client().search_code(repository, query)
    return json.dumps({"query": query, "matches": [
        {"path": item.get("path"), "sha": item.get("sha"), "url": item.get("html_url")}
        for item in result.get("items", [])
    ]})


@mcp.tool()
def list_repository(repository: str, path: str = "", ref: str = "main") -> str:
    """List files or directories at a repository path."""
    result = client().list_repository(repository, path, ref)
    return json.dumps([{"name": x.get("name"), "path": x.get("path"), "type": x.get("type")} for x in result])


if __name__ == "__main__":
    mcp.run()
