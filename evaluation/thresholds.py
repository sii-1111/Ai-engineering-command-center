from collections.abc import Iterable

from .models import EvaluationResult


def assert_quality_gate(
    results: Iterable[EvaluationResult],
    *,
    min_overall: float = 0.80,
    max_latency_ms: float = 5000.0,
    max_cost_usd: float = 0.25,
) -> None:
    failures = []
    for result in results:
        if result.overall < min_overall:
            failures.append(result.case_id + ": overall below threshold")
        if result.latency_ms > max_latency_ms:
            failures.append(result.case_id + ": latency above threshold")
        if result.cost_usd > max_cost_usd:
            failures.append(result.case_id + ": cost above threshold")
    if failures:
        raise AssertionError("Evaluation quality gate failed: " + "; ".join(failures))
