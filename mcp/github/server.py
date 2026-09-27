from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP


@dataclass(frozen=True)
class GitHubConfig:
    repository: str


mcp = FastMCP("github-engineering-tools")


@mcp.tool()
def read_file(repository: str, path: str, ref: str = "main") -> str:
    """Read a repository file through the GitHub MCP boundary.

    The first implementation is intentionally adapter-oriented. The runtime will
    inject the authenticated GitHub client instead of embedding credentials here.
    """
    return f"GitHub adapter placeholder: read {repository}/{path}@{ref}"


@mcp.tool()
def search_code(repository: str, query: str) -> str:
    """Search repository code for an engineering investigation."""
    return f"GitHub adapter placeholder: search {repository} for {query!r}"


if __name__ == "__main__":
    mcp.run()
