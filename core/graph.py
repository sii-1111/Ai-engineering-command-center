from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agents.llm_planner import build_dynamic_plan, decide_next_action, prepare_change_plan
from agents.tool_executor import execute_approved_change, execute_next_tool, verify_change
from core.state.models import EngineeringState

_CHECKPOINTER = InMemorySaver()


def route_after_decision(state: EngineeringState) -> str:
    return "report" if state.get("status") == "investigation_complete" else "execute_tool"


def produce_report(state: EngineeringState) -> EngineeringState:
    report = state.get("report", {})
    return {
        **state,
        "final_report": (
            f"Root Cause: {report.get('root_cause', 'Not established')}\n"
            f"Evidence: {report.get('evidence', [])}\n"
            f"Impact: {report.get('impact', 'Not established')}\n"
            f"Recommended Change: {report.get('recommended_change', 'None')}\n"
            f"Files Involved: {report.get('files_involved', [])}\n"
            f"Confidence: {report.get('confidence', 0.0):.2f}\n"
            f"Approval Required: {report.get('approval_required', False)}\n"
            f"Tool Calls: {len(state.get('tool_calls', []))}"
        ),
        "status": "report_ready",
    }


def approval_gate(state: EngineeringState) -> EngineeringState:
    report = state.get("report", {})
    if not report.get("approval_required", False):
        return {**state, "approval_status": "not_required", "status": "completed"}

    plan = state.get("change_plan", {})
    decision = interrupt({
        "type": "approval_required",
        "message": "Approve this exact change plan before any repository write.",
        "report": report,
        "change_plan": plan,
    })
    approved = bool(decision)
    return {
        **state,
        "approval_status": "approved" if approved else "rejected",
        "status": "approved" if approved else "rejected",
        "approval_request": {"type": "approval_required", "decision": approved},
    }


def route_after_approval(state: EngineeringState) -> str:
    return "execute_change" if state.get("approval_status") == "approved" else END


def build_graph():
    graph = StateGraph(EngineeringState)
    graph.add_node("planner", build_dynamic_plan)
    graph.add_node("execute_tool", execute_next_tool)
    graph.add_node("decide_next", decide_next_action)
    graph.add_node("report", produce_report)
    graph.add_node("prepare_change", prepare_change_plan)
    graph.add_node("approval_gate", approval_gate)
    graph.add_node("execute_change", execute_approved_change)
    graph.add_node("verify_change", verify_change)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "execute_tool")
    graph.add_edge("execute_tool", "decide_next")
    graph.add_conditional_edges("decide_next", route_after_decision)
    graph.add_edge("report", "prepare_change")
    graph.add_edge("prepare_change", "approval_gate")
    graph.add_conditional_edges("approval_gate", route_after_approval)
    graph.add_edge("execute_change", "verify_change")
    graph.add_edge("verify_change", END)
    return graph.compile(checkpointer=_CHECKPOINTER)
