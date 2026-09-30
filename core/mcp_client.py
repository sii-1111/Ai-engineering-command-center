import asyncio
import os
import sys
import json
from typing import Any

from mcp.client.stdio import stdio_client

from core.security.tool_policy import DEFAULT_TOOL_POLICY
from mcp import ClientSession, StdioServerParameters


def _extract_tool_result(result: Any) -> str:
    parts: list[str] = []
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(str(text))
            continue
        if isinstance(item, dict):
            if item.get("text"):
                parts.append(str(item["text"]))
            elif item.get("data") is not None:
                parts.append(json.dumps(item["data"]))
            else:
                parts.append(json.dumps(item))
            continue
        try:
            dumped = item.model_dump()
        except AttributeError:
            dumped = None
        if dumped:
            if dumped.get("text"):
                parts.append(str(dumped["text"]))
            elif dumped.get("data") is not None:
                parts.append(json.dumps(dumped["data"]))
            else:
                parts.append(json.dumps(dumped))

    structured = getattr(result, "structuredContent", None) or getattr(result, "structured_content", None)
    if structured:
        parts.append(json.dumps(structured))
    if not parts:
        try:
            dumped = result.model_dump()
        except AttributeError:
            dumped = None
        if dumped:
            parts.append(json.dumps(dumped))
    return "\n".join(parts)


async def call_github_tool(
    tool_name: str,
    arguments: dict[str, Any],
    agent: str = "unknown",
) -> str:
    DEFAULT_TOOL_POLICY.enforce(agent, tool_name)
    server = StdioServerParameters(
        command=os.getenv("PYTHON_BIN") or sys.executable,
        args=["-m", "tooling.github.server"],
        env=dict(os.environ),
    )
    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool(tool_name, arguments)
        return _extract_tool_result(result)

def call_github_tool_sync(
    tool_name: str,
    arguments: dict[str, Any],
    agent: str = "unknown",
) -> str:
    return asyncio.run(call_github_tool(tool_name, arguments, agent=agent))
