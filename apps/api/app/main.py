from fastapi import FastAPI
from pydantic import BaseModel

from core.graph import build_graph

app = FastAPI(
    title="AI Engineering Command Center",
    version="0.1.0",
    description="Agentic engineering investigation platform.",
)


class TaskRequest(BaseModel):
    task: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/tasks")
async def create_task(request: TaskRequest) -> dict:
    graph = build_graph()
    result = graph.invoke({
        "task": request.task,
        "evidence": [],
        "findings": [],
        "tool_calls": [],
        "status": "started",
    })
    return result
