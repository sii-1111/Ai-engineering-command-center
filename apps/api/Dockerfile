FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY apps /app/apps
COPY agents /app/agents
COPY core /app/core
COPY mcp /app/mcp
COPY tests /app/tests

RUN pip install --no-cache-dir -e .

CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
