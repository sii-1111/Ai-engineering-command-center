# Local Command Center Demo

This guide runs the real Next.js Command Center against the FastAPI backend.

## Prerequisites

- Python 3.11+
- Node.js 20+
- npm
- Git

## 1. Start the API

From the repository root:

```bash
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install the project:

```bash
python -m pip install -e '.[dev]'
```

Copy `.env.example` to `.env`, set `LLM_PROVIDER=gemini`, and add your Gemini
API key to `GEMINI_API_KEY` in that ignored file. Never put the key in source or
the web app. Azure remains available by setting `LLM_PROVIDER=azure` instead.

Start the FastAPI service with the repository's actual application entrypoint:

```bash
uvicorn apps.api.app.main:app --reload --port 8000 --env-file .env
```

The API should be reachable at `http://localhost:8000`.

## 2. Configure and start the web app

Open a second terminal:

```bash
cd apps/web
copy .env.example .env.local
npm install
npm run dev
```

On macOS / Linux, use:

```bash
cp .env.example .env.local
```

The frontend defaults to `NEXT_PUBLIC_API_URL=http://localhost:8000`.

Open `http://localhost:3000`.

## 3. Demo flow

1. Enter an engineering investigation request.
2. Enter the target GitHub repository.
3. Click **Run investigation**.
4. Watch the LangGraph stages update through the Command Center.
5. Review evidence and the execution timeline.
6. When the task reaches human approval, approve or reject the proposed mutation.
7. Review verification, evaluation, and pull-request information.

## Architecture

```text
Browser
  ↓
Next.js Command Center :3000
  ↓
FastAPI Task API :8000
  ↓
LangGraph orchestration
  ↓
Agents → MCP tools → GitHub
  ↓
Evidence / verification / evaluation
```

## CI safety

This local-demo setup does not change `.github/workflows/ci.yml` and adds no runtime dependency. The frontend API URL is configurable through `NEXT_PUBLIC_API_URL`.