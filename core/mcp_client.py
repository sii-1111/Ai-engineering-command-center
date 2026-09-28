import asyncio
import os
from typing import Any

from core.security.tool_policy import DEFAULT_TOOL_POLICY
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def call_github_tool(
    tool_name: str,
    arguments: dict[str, Any],
    agent: str = "unknown",
) -> str:
    DEFAULT_TOOL_POLICY.enforce(agent, tool_name)
    server = StdioServerParameters(
        command=os.getenv("PYTHON_BIN", "python"),
        args=["-m", "tooling.github.server"],
        env=dict(os.environ),
    )
    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool(tool_name, arguments)
        return "\n".join(c.text for c in result.content if getattr(c, "text", None))


def call_github_tool_sync(
    tool_name: str,
    arguments: dict[str, Any],
    agent: str = "unknown",
) -> str:
    return asyncio.run(call_github_tool(tool_name, arguments, agent=agent))
