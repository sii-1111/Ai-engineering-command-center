from fastapi import FastAPI

app = FastAPI(
    title="AI Engineering Command Center",
    version="0.1.0",
    description="Agentic engineering investigation platform.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
