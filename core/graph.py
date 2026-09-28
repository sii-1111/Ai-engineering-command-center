from langgraph.graph import END, START, StateGraph

from agents.llm_planner import build_dynamic_plan
from agents.tool_executor import execute_dynamic_plan
from core.state.models import EngineeringState


def produce_report(state: EngineeringState) -> EngineeringState:
    return {
        **state,
        "final_report": (
            f"Task: {state['task']}\\n"
            f"Repository: {state['repository']}\\n"
            f"Dynamic steps: {len(state.get('dynamic_plan', []))}\\n"
            f"Evidence items: {len(state.get('evidence', []))}\\n"
            f"Tool calls: {len(state.get('tool_calls', []))}"
        ),
        "status": "completed",
    }


def build_graph():
    graph = StateGraph(EngineeringState)
    graph.add_node("planner", build_dynamic_plan)
    graph.add_node("execute_tools", execute_dynamic_plan)
    graph.add_node("report", produce_report)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "execute_tools")
    graph.add_edge("execute_tools", "report")
    graph.add_edge("report", END)
    return graph.compile()
