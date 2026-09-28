import json

from core.llm import LLM
from core.state.models import EngineeringState

SYSTEM = """You are an AI software engineering investigator. Create a minimal investigation plan.
Return JSON only: {\"steps\":[{\"tool\":\"search_code|list_repository|read_file\",\"arguments\":{...}}]}.
Never modify files. Prefer search_code first, then inspect only relevant files. Keep at most 5 steps."""


def build_dynamic_plan(state: EngineeringState) -> EngineeringState:
    prompt = json.dumps({
        "task": state["task"],
        "repository": state["repository"],
        "ref": state.get("ref", "main"),
    })
    plan = LLM().invoke_json([
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
    ])
    steps = plan.get("steps", [])[:5]
    return {**state, "dynamic_plan": steps, "current_step": 0, "status": "plan_ready"}
