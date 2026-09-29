from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    task: str
    expected_facts: tuple[str, ...] = ()
    expected_tools: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    groundedness: float
    completeness: float
    tool_accuracy: float
    latency_ms: float
    cost_usd: float = 0.0

    @property
    def overall(self) -> float:
        return (self.groundedness + self.completeness + self.tool_accuracy) / 3
