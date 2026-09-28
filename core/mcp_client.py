import asyncio
import os
from typing import Any

from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters


async def call_github_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    server = StdioServerParameters(
        command=os.getenv("PYTHON_BIN", "python"),
        args=["-m", "tooling.github.server"],
        env=dict(os.environ),
    )
    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool(tool_name, arguments)
        return "\n".join(c.text for c in result.content if getattr(c, "text", None))


def call_github_tool_sync(tool_name: str, arguments: dict[str, Any]) -> str:
    return asyncio.run(call_github_tool(tool_name, arguments))
