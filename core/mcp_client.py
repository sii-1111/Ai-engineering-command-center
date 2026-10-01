import asyncio
import json
import os
import sys
from typing import Any

from mcp.client.stdio import stdio_client

from core.security.tool_policy import DEFAULT_TOOL_POLICY
from mcp import ClientSession, StdioServerParameters


def _extract_tool_result(result: Any) -> str:
    """Normalize MCP text/structured responses into evidence the agent can inspect."""
    parts: list[str] = []
    seen: set[str] = set()

    def add(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            if value.strip() and value not in seen:
                seen.add(value)
                parts.append(value)
            return
        if isinstance(value, (dict, list)):
            serialized = json.dumps(value)
            if serialized not in seen:
                seen.add(serialized)
                parts.append(serialized)
            return
        add(str(value))

    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            add(text)
            continue
        if isinstance(item, dict):
            add(item.get("text"))
            add(item.get("data"))
            if not item.get("text") and item.get("data") is None:
                add(item)
            continue
        try:
            dumped = item.model_dump(mode="json")
        except (AttributeError, TypeError):
            dumped = None
        if dumped:
            add(dumped.get("text"))
            add(dumped.get("data"))
            if not dumped.get("text") and dumped.get("data") is None:
                add(dumped)

    structured = getattr(result, "structuredContent", None) or getattr(result, "structured_content", None)
    if structured is not None:
        if isinstance(structured, dict) and set(structured) == {"result"}:
            add(structured["result"])
        else:
            add(structured)

    if not parts:
        try:
            dumped = result.model_dump(mode="json")
        except TypeError:
            dumped = result.model_dump()
        except AttributeError:
            dumped = None
        if dumped:
            add(dumped.get("content"))
            add(dumped.get("structuredContent"))
            add(dumped.get("structured_content"))
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
