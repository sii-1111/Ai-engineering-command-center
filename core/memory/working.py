"""Task-scoped working memory for LangGraph investigations.

The memory is intentionally small and deterministic: it keeps the latest
bounded set of evidence, tool calls, decisions, and a compact task summary.
LangGraph checkpointing remains the source of truth for resumability.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Any

MAX_EVIDENCE = 40
MAX_TOOL_CALLS = 40
MAX_DECISIONS = 20


@dataclass
class WorkingMemory:
    task_id: str
    summary: str = ""
    evidence: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=MAX_EVIDENCE))
    tool_calls: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=MAX_TOOL_CALLS))
    decisions: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=MAX_DECISIONS))

    def add_evidence(self, source: str, detail: str) -> None:
        self.evidence.append({"source": source, "detail": detail})

    def add_tool_call(self, tool: str, arguments: dict[str, Any], status: str = "completed") -> None:
        self.tool_calls.append({"tool": tool, "arguments": arguments, "status": status})

    def add_decision(self, decision: str, reason: str = "") -> None:
        self.decisions.append({"decision": decision, "reason": reason})

    def update_summary(self, summary: str) -> None:
        self.summary = summary

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "summary": self.summary,
            "evidence": list(self.evidence),
            "tool_calls": list(self.tool_calls),
            "decisions": list(self.decisions),
        }

    @classmethod
    def from_state(cls, task_id: str, state: dict[str, Any]) -> "WorkingMemory":
        memory = cls(task_id=task_id, summary=str(state.get("memory_summary", "")))
        for item in state.get("evidence", []):
            memory.evidence.append(dict(item))
        for item in state.get("tool_calls", []):
            memory.tool_calls.append(dict(item))
        for item in state.get("memory_decisions", []):
            memory.decisions.append(dict(item))
        return memory


def memory_to_state(memory: WorkingMemory) -> dict[str, Any]:
    return {
        "memory_summary": memory.summary,
        "evidence": list(memory.evidence),
        "tool_calls": list(memory.tool_calls),
        "memory_decisions": list(memory.decisions),
    }
