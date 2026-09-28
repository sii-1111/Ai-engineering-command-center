# AI Engineering Command Center

> An agentic AI platform that investigates real engineering problems, uses tools, proposes fixes, runs verification, and pauses for human approval before risky actions.

## Why this project exists

Most AI coding demos stop at code generation. The Command Center is designed around a harder problem:

**Give an AI engineer a real engineering task and let it investigate, reason, use tools, validate the result, and produce an evidence-backed outcome.**

Example:

> Analyze this repository and find why the `/search` endpoint is slow. Identify the root cause, propose a fix, run tests, and prepare the change for review.

## Architecture

### Interactive GitDiagram

Explore the repository architecture interactively in GitDiagram:

[Open AI Engineering Command Center in GitDiagram](https://gitdiagram.com/sii-1111/Ai-engineering-command-center)


```mermaid
flowchart TD
    U[Engineer] --> UI[Web Command Center]
    UI --> API[FastAPI API]
    API --> G[LangGraph Runtime]
    G --> P[Planner / Commander]
    P --> R[Research Agent]
    P --> C[Code Agent]
    P --> T[Testing Agent]
    P --> V[Reviewer Agent]

    R --> MCP[MCP Tool Layer]
    C --> MCP
    T --> MCP
    V --> MCP

    MCP --> GH[GitHub]
    MCP --> FS[Filesystem]
    MCP --> TERM[Sandboxed Terminal]
    MCP --> DB[Database]
    MCP --> WEB[Web / Docs]

    G --> MEM[State + Memory]
    MEM --> PG[(PostgreSQL)]
    MEM --> REDIS[(Redis)]

    R --> SEARCH[Azure AI Search]
    SEARCH --> BLOB[Azure Blob Storage]

    G --> HITL{Human Approval}
    HITL -->|approved| MCP
    HITL -->|rejected| G

    G --> EVAL[Evaluation + Observability]
    EVAL --> OTEL[OpenTelemetry / Tracing]
```

## Core capabilities

- **Planner / Commander** — decomposes an engineering request into executable steps.
- **Specialized agents** — research, code, testing, and review roles.
- **MCP-first tooling** — tools are exposed through a consistent Model Context Protocol boundary.
- **Human-in-the-loop** — risky mutations require explicit approval.
- **Repository intelligence** — code search, file inspection, dependency analysis, and test execution.
- **Grounded investigation** — retrieval and evidence are carried into agent decisions.
- **Evaluation** — tool-call success, task completion, groundedness, latency, cost, recovery, and human intervention.
- **Observability** — capture task events, evaluation metrics, and engineering outcomes.

## Current stack

| Layer | Technology |
|---|---|
| Frontend | Next.js / TypeScript |
| API | FastAPI / Python |
| Orchestration | LangGraph |
| Models | Azure OpenAI |
| Tool protocol | MCP |
| Retrieval | Azure AI Search |
| Object storage | Azure Blob Storage |
| State | PostgreSQL + Redis |
| Runtime | Docker |
| CI/CD | GitHub Actions |
| Evaluation | RAGAS + custom agent evals |
| Observability | OpenTelemetry + LangSmith |

## Repository structure

```text
.
├── apps/
│   ├── api/                 # FastAPI service
│   └── web/                 # Next.js command center
├── agents/                  # Agent roles and prompts
├── core/
│   ├── evaluation/          # Agent/task evaluation
│   ├── memory/              # Working and persistent memory
│   ├── security/            # Approval and tool policies
│   └── state/               # LangGraph state
├── tooling/              # MCP-backed engineering tools
│   └── github/              # GitHub MCP server and client
├── infrastructure/          # Docker and deployment assets
├── tests/                   # Unit/integration/evaluation tests
├── docs/                    # Architecture and ADRs
└── .github/workflows/       # CI/CD
```

## Engineering principles

1. **Read before write.**
2. **Evidence before conclusion.**
3. **Least-privilege tools.**
4. **Human approval for consequential mutations.**
5. **Every important claim should be traceable to evidence.**
6. **Measure agent behavior instead of assuming it works.**
7. **Design for failure, recovery, and observability.**

## Roadmap

### Phase 1 — Engineering investigation
- [x] LangGraph state graph
- [x] GitHub MCP tools
- [x] Repository/code investigation
- [x] Test/check verification
- [x] Evidence-backed investigation report

### Phase 2 — Agentic orchestration
- [x] Planner
- [x] Research / investigation agent
- [x] Code modification flow
- [x] Verification flow
- [x] Reviewer / Critic Agent
- [x] Interrupt/resume HITL flow

### Phase 3 — Knowledge + memory
- [x] PostgreSQL-backed LangGraph checkpoint foundation
- [x] Optional Redis task snapshot store and health signal
- [ ] Azure Blob ingestion
- [x] Repository retrieval abstraction
- [x] Azure AI Search hybrid retrieval
- [ ] Working memory
- [ ] Long-term engineering knowledge
- [ ] Repository-aware RAG

### Phase 4 — Production engineering
- [x] Evaluation framework
- [x] Task observability events
- [ ] Cost/latency dashboards
- [ ] Dockerized services
- [x] CI/CD validation
- [ ] Azure deployment

## Project status

**Active development — production-style AI engineering platform.**

The foundation is now implemented and the project has progressed beyond the initial architecture scaffold. The current system supports end-to-end engineering investigation: task planning with LangGraph, bounded repository investigation through MCP, evidence-backed root-cause analysis, confidence scoring, human approval before mutations, automated branch/PR creation, verification, reviewer/critic analysis, evaluation metrics, observability events, and a recruiter-facing Next.js Command Center.

The current focus is **production hardening and deployment** — expanding live infrastructure integrations, strengthening evaluation and observability, improving security and tool isolation, and deploying the platform as a fully accessible application.
