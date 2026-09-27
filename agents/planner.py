from core.state.models import EngineeringState


def build_plan(state: EngineeringState) -> EngineeringState:
    task = state["task"]
    plan = [
        "Understand the engineering request and identify the repository evidence needed.",
        "Inspect relevant GitHub files and repository structure.",
        "Collect evidence and identify likely root causes or implementation constraints.",
        "Produce an evidence-backed engineering report.",
    ]
    return {**state, "plan": plan, "current_step": 0, "status": f"planned: {task}"}
