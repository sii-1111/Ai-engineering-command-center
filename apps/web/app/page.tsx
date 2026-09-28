"use client";

import { useEffect, useMemo, useState } from "react";

type Stage = { name: string; state: "done" | "active" | "idle" };
type TaskResult = {
  task_id: string;
  status: string;
  approval_status?: string;
  approval_request?: unknown;
  report?: Record<string, unknown>;
  final_report?: string;
  verification_status?: string;
  verification_result?: Record<string, unknown>;
  pull_request?: Record<string, unknown>;
  review?: Record<string, unknown>;
  evaluation?: Record<string, unknown>;
  observability_events?: Array<Record<string, unknown>>;
};

const stageNames = ["Planner", "Repository investigation", "Root-cause analysis", "Human approval", "Code change", "Verification", "Reviewer"];

function stagesFor(data?: TaskResult): Stage[] {
  if (!data) return stageNames.map(name => ({ name, state: "idle" }));
  const status = data.status;
  const approval = data.approval_status;
  const review = data.review || {};
  const verification = data.verification_status;
  const states: Stage[] = stageNames.map(name => ({ name, state: "idle" }));
  states[0].state = "done";
  states[1].state = "done";
  states[2].state = data.report ? "done" : "active";
  if (status === "awaiting_approval") {
    states[3].state = "active";
  } else if (approval && approval !== "not_required") {
    states[3].state = "done";
  }
  if (data.pull_request && Object.keys(data.pull_request).length) states[4].state = "done";
  else if (approval === "approved") states[4].state = "active";
  if (verification === "passed" || verification === "failed") states[5].state = "done";
  else if (data.pull_request && Object.keys(data.pull_request).length) states[5].state = "active";
  if (Object.keys(review).length) states[6].state = "done";
  else if (verification === "passed" || verification === "failed") states[6].state = "active";
  return states;
}

function metricValue(data: TaskResult | undefined, key: string): string {
  const evaluation = data?.evaluation || {};
  const candidates: Record<string, unknown> = {
    Evidence: evaluation.evidence_count ?? data?.report?.evidence_count,
    "Tool calls": evaluation.tool_call_count,
    Confidence: evaluation.confidence != null ? `${Math.round(Number(evaluation.confidence) * 100)}%` : undefined,
    Latency: evaluation.latency_seconds != null ? `${Number(evaluation.latency_seconds).toFixed(1)}s` : undefined,
  };
  return candidates[key] == null ? "—" : String(candidates[key]);
}

export default function Home() {
  const [task, setTask] = useState("Analyze this repository and find why the /search endpoint is slow. Identify the root cause, propose a fix, run tests, and prepare the change for review.");
  const [repo, setRepo] = useState("sii-1111/Ai-engineering-command-center");
  const [running, setRunning] = useState(false);
  const [data, setData] = useState<TaskResult>();
  const [error, setError] = useState("");
  const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  const stages = useMemo(() => stagesFor(data), [data]);
  const metrics = ["Evidence", "Tool calls", "Confidence", "Latency"];

  useEffect(() => {
    if (!data?.task_id || data.status === "completed") return;
    const timer = window.setInterval(async () => {
      try {
        const res = await fetch(`${api}/v1/tasks/${data.task_id}`);
        if (res.ok) setData(await res.json());
      } catch {
        // Keep the last known state when the API is temporarily unavailable.
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [api, data?.task_id, data?.status]);

  async function runTask() {
    setRunning(true); setError(""); setData(undefined);
    try {
      const res = await fetch(`${api}/v1/tasks`, {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({task, repository: repo, ref:"main"})
      });
      if (!res.ok) throw new Error(`Task API returned ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to start task");
    } finally { setRunning(false); }
  }

  async function approval(value: boolean) {
    if (!data?.task_id) return;
    setRunning(true); setError("");
    try {
      const res = await fetch(`${api}/v1/tasks/${data.task_id}/approval`, {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({approved: value})
      });
      if (!res.ok) throw new Error(`Approval API returned ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to submit approval");
    } finally { setRunning(false); }
  }

  const evidence = Array.isArray(data?.report?.evidence) ? data?.report?.evidence as unknown[] : [];
  const reportText = data?.final_report || (data?.report ? JSON.stringify(data.report, null, 2) : "Run an investigation to populate live engineering evidence.");
  const waitingApproval = data?.status === "awaiting_approval";

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="logo">✦</div>AI Engineering Command Center</div>
      <div className="nav"><div className="active">Command Center</div><div>Investigations</div><div>Evidence</div><div>Evaluations</div><div>Settings</div></div>
      <div className="sidefoot">Agentic engineering workspace<br/>LangGraph · MCP · GitHub · Azure OpenAI</div>
    </aside>
    <main>
      <header className="top"><div><div className="eyebrow">Production engineering workspace</div><h1 className="title">Turn engineering questions into verified changes.</h1><div className="sub">Plan → investigate → approve → change → verify → review.</div></div><div className="status">● {data?.status?.toUpperCase() ?? "SYSTEM READY"}</div></header>

      <section className="grid">
        <div className="panel"><h2>New engineering task</h2><textarea className="taskbox" value={task} onChange={e=>setTask(e.target.value)} /><div className="controls"><input className="input" value={repo} onChange={e=>setRepo(e.target.value)} aria-label="Repository" /><button className="primary" onClick={runTask} disabled={running}>{running ? "Running…" : "Run investigation →"}</button></div>{error && <div className="error">{error}</div>}</div>
        <div className="panel"><h2>Execution pipeline</h2><div className="steps">{stages.map(s=><div className={`step ${s.state}`} key={s.name}><i className="dot"/><span>{s.name}</span><small>{s.state === "done" ? "DONE" : s.state === "active" ? "ACTIVE" : "WAITING"}</small></div>)}</div></div>
      </section>

      <section className="metrics">{metrics.map(label=><div className="metric" key={label}><span>{label}</span><b>{metricValue(data,label)}</b></div>)}</section>

      <section className="bottom">
        <div className="panel"><h2>Evidence trail</h2><div className="evidence">
          {evidence.length ? evidence.map((item, i)=><div className="row" key={i}><code>evidence {i+1}</code><br/>{typeof item === "string" ? item : JSON.stringify(item)}</div>) : <div className="row">No evidence returned yet. Start an investigation to populate this panel.</div>}
        </div></div>
        <div className="panel"><h2>Engineering outcome</h2><div className="review"><div><b>{waitingApproval ? "Approval required" : data?.status === "completed" ? "Investigation complete" : "Awaiting execution"}</b><div className="sub">{waitingApproval ? "Review the proposed mutation before execution." : "Outcome is populated directly from the task state."}</div></div><span className={`pill ${waitingApproval ? "warn" : "pass"}`}>{waitingApproval ? "HITL" : data?.status?.toUpperCase() ?? "READY"}</span></div><div style={{marginTop:12}}><div className="row"><code>Task ID</code><br/>{data?.task_id ?? "—"}</div><div className="row"><code>Final report</code><br/><pre>{reportText}</pre></div>{waitingApproval && <div className="controls"><button className="primary" onClick={()=>approval(true)} disabled={running}>Approve change</button><button className="secondary" onClick={()=>approval(false)} disabled={running}>Reject</button></div>}{Boolean(data?.pull_request && Object.keys(data.pull_request).length) && <div className="row"><code>Pull request</code><br/>{String(data?.pull_request?.url ?? "Created")}</div>}</div></div>
      </section>
    </main>
  </div>;
}
