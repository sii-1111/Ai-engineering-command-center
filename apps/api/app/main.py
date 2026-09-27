from fastapi import FastAPI
from pydantic import BaseModel, Field

from core.graph import build_graph

app = FastAPI(title="AI Engineering Command Center", version="0.1.0")


class TaskRequest(BaseModel):
    task: str = Field(min_length=1)
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    ref: str = "main"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/tasks")
async def create_task(request: TaskRequest) -> dict:
    return build_graph().invoke({
        "task": request.task,
        "repository": request.repository,
        "ref": request.ref,
        "evidence": [],
        "findings": [],
        "tool_calls": [],
        "status": "started",
    })
