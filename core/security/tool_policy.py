from dataclasses import dataclass

RISK_LEVELS = {
    "read_file": "low",
    "search_code": "low",
    "list_repository": "low",
    "search_repository_rag": "low",\n    "search_engineering_knowledge": "low",
    "get_commit_checks": "low",
    "create_branch": "medium",
    "update_file": "high",
    "create_pull_request": "high",
    "terminal": "critical",
}

AGENT_TOOL_ALLOWLIST = {
    "research_agent": {
        "search_code",
        "read_file",
        "list_repository",
        "search_repository_rag",\n        "search_engineering_knowledge",
        "get_commit_checks",
    },
    "code_agent": {"read_file", "create_branch", "update_file", "create_pull_request"},
    "reviewer_agent": {"search_code", "read_file", "list_repository", "get_commit_checks"},
    "verification_agent": {"get_commit_checks"},
}


@dataclass(frozen=True)
class ToolDecision:
    allowed: bool
    agent: str
    tool: str
    risk: str
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "agent": self.agent,
            "tool": self.tool,
            "risk": self.risk,
            "reason": self.reason,
        }


class ToolPermissionError(PermissionError):
    def __init__(self, decision: ToolDecision) -> None:
        self.decision = decision
        super().__init__(decision.reason)


class ToolPolicy:
    """Central allowlist and risk policy for MCP tool execution."""

    def authorize(self, agent: str, tool: str) -> ToolDecision:
        risk = RISK_LEVELS.get(tool, "critical")
        allowed_tools = AGENT_TOOL_ALLOWLIST.get(agent, set())
        if tool not in RISK_LEVELS:
            return ToolDecision(False, agent, tool, risk, "Unknown tool is blocked by default.")
        if tool not in allowed_tools:
            return ToolDecision(
                False,
                agent,
                tool,
                risk,
                f"Agent '{agent}' is not permitted to execute '{tool}'.",
            )
        return ToolDecision(True, agent, tool, risk, "Tool permitted by agent policy.")

    def enforce(self, agent: str, tool: str) -> ToolDecision:
        decision = self.authorize(agent, tool)
        if not decision.allowed:
            raise ToolPermissionError(decision)
        return decision


DEFAULT_TOOL_POLICY = ToolPolicy()
