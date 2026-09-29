from evaluation.models import EvaluationResult
from evaluation.scoring import coverage_score, groundedness_score
from evaluation.thresholds import assert_quality_gate


def test_coverage_score():
    assert coverage_score(["GitHub", "tests"], ["github", "tests", "search"]) == 1.0


def test_groundedness_requires_supported_facts():
    assert groundedness_score("The root cause is repository evidence.", ["root cause", "repository evidence"]) == 1.0
    assert groundedness_score("No evidence.", ["root cause"]) == 0.0


def test_quality_gate_accepts_good_result():
    assert_quality_gate([EvaluationResult("ok", 1.0, 1.0, 1.0, 100.0, 0.01)])


def test_quality_gate_rejects_regression():
    try:
        assert_quality_gate([EvaluationResult("bad", 0.5, 0.5, 0.5, 100.0, 0.01)])
    except AssertionError as exc:
        assert "bad" in str(exc)
    else:
        raise AssertionError("Expected quality gate failure")
