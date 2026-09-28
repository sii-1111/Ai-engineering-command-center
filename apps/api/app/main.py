from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from pydantic import BaseModel, Field

from agents.tool_executor import verify_change
from core.evaluation import evaluate_task
from core.graph import build_graph

app = FastAPI(title="AI Engineering Command Center", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
graph = build_graph()


class TaskRequest(BaseModel):
    task: str = Field(min_length=1)
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    ref: str = "main"


class ApprovalRequest(BaseModel):
    approved: bool


def _config(task_id: str) -> dict:
    return {"configurable": {"thread_id": task_id}}


def _serialize_result(task_id: str, result: dict) -> dict:
    interrupts = result.get("__interrupt__", ())
    if interrupts:
        request = interrupts[0].value
        return {
            "task_id": task_id,
            "status": "awaiting_approval",
            "approval_request": request,
            "report": result.get("report", {}),
            "final_report": result.get("final_report", ""),
        }
    return {
        "task_id": task_id,
        "status": result.get("status", "completed"),
        "report": result.get("report", {}),
        "final_report": result.get("final_report", ""),
        "approval_status": result.get("approval_status", "not_required"),
        "verification_status": result.get("verification_status", "not_started"),
        "verification_result": result.get("verification_result", {}),
        "pull_request": result.get("pull_request", {}),
        "review": result.get("review", {}),
        "evaluation": result.get("evaluation", {}),
        "observability_events": result.get("observability_events", []),
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/tasks")
async def create_task(request: TaskRequest) -> dict:
    task_id = str(uuid4())
    result = graph.invoke(
        {
            "task": request.task,
            "repository": request.repository,
            "ref": request.ref,
            "evidence": [],
            "findings": [],
            "tool_calls": [],
            "status": "started",
            "observability_events": [{"timestamp": "task-created", "event": "task_started"}],
        },
        config=_config(task_id),
    )
    return _serialize_result(task_id, result)


@app.get("/v1/tasks/{task_id}")
async def get_task(task_id: str) -> dict:
    state = graph.get_state(_config(task_id))
    if not state.values:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize_result(task_id, state.values)


@app.post("/v1/tasks/{task_id}/approval")
async def submit_approval(task_id: str, request: ApprovalRequest) -> dict:
    state = graph.get_state(_config(task_id))
    if not state.values:
        raise HTTPException(status_code=404, detail="Task not found")

    result = graph.invoke(Command(resume=request.approved), config=_config(task_id))
    return _serialize_result(task_id, result)


@app.get("/v1/tasks/{task_id}/verification")
async def get_verification(task_id: str) -> dict:
    config = _config(task_id)
    state = graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Task not found")

    verified = verify_change(state.values)
    graph.update_state(config, verified)
    return _serialize_result(task_id, verified)


@app.get("/v1/tasks/{task_id}/evaluation")
async def get_evaluation(task_id: str) -> dict:
    config = _config(task_id)
    state = graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Task not found")
    evaluated = evaluate_task(state.values)
    graph.update_state(config, evaluated)
    return _serialize_result(task_id, evaluated)
