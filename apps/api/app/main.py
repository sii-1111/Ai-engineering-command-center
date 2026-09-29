rrom uuid import uuid4

rrom fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from pydantic import BaseModel, Field

from agents.tool_executor import verify_change
from core.evaluation import evaluate_task
from core.graph import build_graph
from core.store.redis import healthcheck as redis_healthcheck
from core.store.redis import save_task_snapshot
from core.store.tasks import TaskStore, build_task_record
from core.store.jobs import JobStore

app = FastAPI(title="AI Engineering Command Center", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
graph = build_graph()
task_store = TaskStore()
job_store = JobStore()


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
        "knowledge_promoted": result.get("knowledge_promoted", False),
        "knowledge_id": result.get("knowledge_id", ""),
    }


@app.get("/health")
async def health() -> dict[str, str]:
    redis_healthcheck()
    return {"status": "ok"}


@app.post("/v1/tasks")
async def create_task(request: TaskRequest) -> dict:
    task_id = str(uuid4())
    task_store.save(build_task_record(task_id, request.task, request.repository, request.ref))
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
    save_task_snapshot(task_id, result)
    task_store.update(task_id, status=result.get("status", "completed"))
    return _serialize_result(task_id, result)


@app.get("/v1/tasks/{task_id}")
async def get_task(task_id: str) -> dict:
    state = graph.get_state(_config(task_id))
    if not state.values:
        raise HTTPException(status_code=404, detail="Task not found")
    record = task_store.get(task_id)
    if record is None and state.values:
        record = build_task_record(task_id, str(state.values.get("task", "")), str(state.values.get("repository", "")), str(state.values.get("ref", "main")))
    return {**_serialize_result(task_id, state.values), "task_metadata": record.as_dict() if record else {}}


@app.post("/v1/tasks/{task_id}/approval")
async def submit_approval(task_id: str, request: ApprovalRequest) -> dict:
    state = graph.get_state(_config(task_id))
    if not state.values:
        raise HTTPException(status_code=404, detail="Task not found")

    result = graph.invoke(Command(resume=request.approved), config=_config(task_id))
    task_store.update(task_id, status=result.get("status", "completed"))
    save_task_snapshot(task_id, result)
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


@app.post("/v1/tasks/{task_id}/jobs")
async def enqueue_task(task_id: str) -> dict:
    if task_store.get(task_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")
    job = job_store.enqueue(task_id)
    if job is None:
        raise HTTPException(status_code=503, detail="Redis job store is not configured")
    return job.as_dict()


@app.get("/v1/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.as_dict()


@app.get("/v1/tasks/{task_id}/evaluation")
async def get_evaluation(task_id: str) -> dict:
    config = _config(task_id)
    state = graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Task not found")
    evaluated = evaluate_task(state.values)
    graph.update_state(config, evaluated)
    return _serialize_result(task_id, evaluated)
