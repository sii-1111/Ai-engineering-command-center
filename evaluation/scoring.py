from collections.abc import Iterable


def coverage_score(expected: Iterable[str], observed: Iterable[str]) -> float:
    expected_set = {str(x).strip().lower() for x in expected if str(x).strip()}
    observed_set = {str(x).strip().lower() for x in observed if str(x).strip()}
    if not expected_set:
        return 1.0
    return len(expected_set & observed_set) / len(expected_set)


def groundedness_score(answer: str, approved_facts: Iterable[str]) -> float:
    facts = [str(x).strip().lower() for x in approved_facts if str(x).strip()]
    if not answer.strip() or not facts:
        return 0.0
    answer_lower = answer.lower()
    return sum(fact in answer_lower for fact in facts) / len(facts)
