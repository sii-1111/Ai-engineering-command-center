"use client";

import { useMemo, useState } from "react";

type Stage = { name: string; state: "done" | "active" | "idle" };
const initialStages: Stage[] = [
  { name: "Planner", state: "done" }, { name: "Repository investigation", state: "done" },
  { name: "Root-cause analysis", state: "done" }, { name: "Human approval", state: "active" },
  { name: "Code change", state: "idle" }, { name: "Verification", state: "idle" }, { name: "Reviewer", state: "idle" },
];

export default function Home() {
  const [task, setTask] = useState("Analyze this repository and find why the /search endpoint is slow. Identify the root cause, propose a fix, run tests, and prepare the change for review.");
  const [repo, setRepo] = useState("sii-1111/Ai-engineering-command-center");
  const [running, setRunning] = useState(false);
  const [approved, setApproved] = useState(false);
  const [stages, setStages] = useState(initialStages);
  const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  const metrics = useMemo(() => [
    ["Evidence", "12"], ["Tool calls", "7"], ["Confidence", "92%"], ["Latency", "4.8s"],
  ], []);

  async function runTask() {
    setRunning(true);
    try {
      const res = await fetch(`${api}/v1/tasks`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({task, repository: repo, ref:"main"}) });
      if (!res.ok) throw new Error("API request failed");
      const data = await res.json();
      if (data.status === "awaiting_approval") {
        setStages(s => s.map(x => x.name === "Human approval" ? {...x,state:"active"} : x));
      }
    } catch { /* Demo remains useful when API is unavailable. */ }
    finally { setRunning(false); }
  }

  async function approval(value: boolean) {
    setApproved(value);
    if (!value) return;
    setStages(s => s.map(x => {
      if (x.name === "Human approval") return {...x,state:"done"};
      if (x.name === "Code change") return {...x,state:"active"};
      return x;
    }));
  }

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="logo">✦</div>AI Engineering Command Center</div>
      <div className="nav"><div className="active">Command Center</div><div>Investigations</div><div>Evidence</div><div>Evaluations</div><div>Settings</div></div>
      <div className="sidefoot">Agentic engineering workspace<br/>LangGraph · MCP · GitHub · Azure OpenAI</div>
    </aside>
    <main>
      <header className="top"><div><div className="eyebrow">Production engineering workspace</div><h1 className="title">Turn engineering questions into verified changes.</h1><div className="sub">Plan → investigate → approve → change → verify → review.</div></div><div className="status">● SYSTEM READY</div></header>

      <section className="grid">
        <div className="panel"><h2>New engineering task</h2><textarea className="taskbox" value={task} onChange={e=>setTask(e.target.value)} /><div className="controls"><input className="input" value={repo} onChange={e=>setRepo(e.target.value)} aria-label="Repository" /><button className="primary" onClick={runTask} disabled={running}>{running ? "Investigating…" : "Run investigation →"}</button></div></div>
        <div className="panel"><h2>Execution pipeline</h2><div className="steps">{stages.map(s=><div className={`step ${s.state}`} key={s.name}><i className="dot"/><span>{s.name}</span><small>{s.state === "done" ? "DONE" : s.state === "active" ? "ACTIVE" : "WAITING"}</small></div>)}</div></div>
      </section>

      <section className="metrics">{metrics.map(([label,value])=><div className="metric" key={label}><span>{label}</span><b>{value}</b></div>)}</section>

      <section className="bottom">
        <div className="panel"><h2>Evidence trail</h2><div className="evidence">
          <div className="row"><code>read_file · core/search.py</code><br/>Search handler performs an unbounded database fetch before filtering.</div>
          <div className="row"><code>search_code · repository</code><br/>The endpoint calls the repository query without a result limit.</div>
          <div className="row"><code>read_file · tests/test_search.py</code><br/>No regression test covers large result sets.</div>
        </div></div>
        <div className="panel"><h2>Engineering outcome</h2><div className="review"><div><b>{approved ? "Approval granted" : "Approval required"}</b><div className="sub">{approved ? "Change execution can continue." : "Review the exact proposed change before mutation."}</div></div><span className={`pill ${approved ? "pass" : "warn"}`}>{approved ? "APPROVED" : "HITL"}</span></div><div style={{marginTop:12}}><div className="row"><code>Root cause</code><br/>Unbounded retrieval increases database work and response latency.</div><div className="controls"><button className="primary" onClick={()=>approval(true)}>Approve change</button><button className="secondary" onClick={()=>approval(false)}>Reject</button></div></div></div>
      </section>
    </main>
  </div>;
}
