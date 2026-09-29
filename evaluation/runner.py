from collections.abc import Callable, Iterable

from .models import BenchmarkCase, EvaluationResult
from .scoring import coverage_score, groundedness_score


def evaluate_case(
    case: BenchmarkCase,
    answer: str,
    observed_tools: Iterable[str],
    approved_facts: Iterable[str],
    elapsed_ms: float,
    cost_usd: float = 0.0,
) -> EvaluationResult:
    return EvaluationResult(
        case_id=case.case_id,
        groundedness=groundedness_score(answer, approved_facts),
        completeness=groundedness_score(answer, case.expected_facts),
        tool_accuracy=coverage_score(case.expected_tools, observed_tools),
        latency_ms=elapsed_ms,
        cost_usd=cost_usd,
    )


def run_benchmark(
    cases: Iterable[BenchmarkCase],
    execute: Callable[[BenchmarkCase], tuple[str, Iterable[str], Iterable[str], float, float]],
) -> list[EvaluationResult]:
    return [evaluate_case(case, *execute(case)) for case in cases]
