from langgraph.graph import END, START, StateGraph

from agents.planner import build_plan
from core.state.models import EngineeringState


def collect_initial_evidence(state: EngineeringState) -> EngineeringState:
    evidence = list(state.get("evidence", []))
    evidence.append({
        "source": "planner",
        "detail": "Investigation plan created; GitHub inspection is the next execution boundary.",
    })
    return {**state, "evidence": evidence, "status": "evidence collection ready"}


def produce_report(state: EngineeringState) -> EngineeringState:
    plan = state.get("plan", [])
    evidence = state.get("evidence", [])
    findings = state.get("findings", [])
    report = (
        f"Task: {state['task']}\\n\\n"
        f"Plan: {plan}\\n\\n"
        f"Findings: {findings or ['No findings yet; GitHub adapter execution is the next step.']}\\n\\n"
        f"Evidence: {evidence}"
    )
    return {**state, "final_report": report, "status": "completed"}


def build_graph():
    graph = StateGraph(EngineeringState)
    graph.add_node("planner", build_plan)
    graph.add_node("collect_evidence", collect_initial_evidence)
    graph.add_node("report", produce_report)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "collect_evidence")
    graph.add_edge("collect_evidence", "report")
    graph.add_edge("report", END)
    return graph.compile()
