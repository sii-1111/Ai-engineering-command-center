from langgraph.graph import END, START, StateGraph

from agents.github_investigator import add_findings, inspect_repository
from agents.planner import build_plan
from core.state.models import EngineeringState


def collect_initial_evidence(state: EngineeringState) -> EngineeringState:
    evidence = list(state.get("evidence", []))
    evidence.append({
        "source": "planner",
        "detail": "Investigation plan created; GitHub inspection is the next execution step.",
    })
    return {**state, "evidence": evidence, "status": "evidence collection ready"}


def produce_report(state: EngineeringState) -> EngineeringState:
    return {
        **state,
        "final_report": (
            f"Task: {state['task']}\\n"
            f"Repository: {state['repository']}\\n"
            f"Findings: {state.get('findings', [])}\\n"
            f"Evidence items: {len(state.get('evidence', []))}\\n"
            f"Tool calls: {len(state.get('tool_calls', []))}"
        ),
        "status": "completed",
    }


def build_graph():
    graph = StateGraph(EngineeringState)
    graph.add_node("planner", build_plan)
    graph.add_node("collect_evidence", collect_initial_evidence)
    graph.add_node("github_inspection", inspect_repository)
    graph.add_node("findings", add_findings)
    graph.add_node("report", produce_report)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "collect_evidence")
    graph.add_edge("collect_evidence", "github_inspection")
    graph.add_edge("github_inspection", "findings")
    graph.add_edge("findings", "report")
    graph.add_edge("report", END)
    return graph.compile()
