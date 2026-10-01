"use client";

import { useRef, useState } from "react";
import type { FormEvent } from "react";

const repoModules = [
  "apps/",
  "agents/",
  "core/",
  "tooling/",
  "tests/",
  "docs/",
];

const agentFlow = [
  { title: "Planner", text: "Breaks the engineering task into evidence-backed steps." },
  { title: "Research", text: "Inspects repo context, code, and retrieval sources." },
  { title: "Code", text: "Implements fixes and updates the relevant files." },
  { title: "Verify", text: "Runs checks and validates behavior with test evidence." },
  { title: "Review", text: "Flags risk and prepares final approval-ready summaries." },
];

const metrics = [
  { label: "Live repos", value: "03" },
  { label: "Active agents", value: "05" },
  { label: "Evaluations", value: "24" },
  { label: "Approval loop", value: "HITL" },
];

function InvestigationResult({ result }: { result: Record<string, unknown> }) {
  const report = (result.report ?? {}) as Record<string, unknown>;
  const evidence = Array.isArray(result.evidence) ? result.evidence : [];
  const toolCalls = Array.isArray(result.tool_calls) ? result.tool_calls : [];
  const review = (result.review ?? {}) as Record<string, unknown>;
  const verification = (result.verification_result ?? {}) as Record<string, unknown>;
  const status = String(result.status ?? "completed");
  const confidence = Number(report.confidence ?? 0);
  const confidencePct = Math.round(Math.max(0, Math.min(1, confidence)) * 100);
  const evidenceItems = evidence.map((item, index) => {
    const entry = (item ?? {}) as Record<string, unknown>;
    return {
      id: String(entry.id ?? `ev-${String(index + 1).padStart(3, "0")}`),
      source: String(entry.source ?? "repository evidence"),
      detail: String(entry.detail ?? ""),
    };
  });

  return (
    <div className="investigation-result">
      <div className="result-summary">
        <div>
          <span className="result-kicker">Investigation complete</span>
          <h3>{status.replaceAll("_", " ")}</h3>
        </div>
        <div className="confidence-ring">
          <strong>{confidencePct}%</strong>
          <span>confidence</span>
        </div>
      </div>

      <div className="result-grid">
        <div className="result-card result-card-wide">
          <span className="result-label">Root cause</span>
          <p>{String(report.root_cause ?? "No root cause established.")}</p>
        </div>
        <div className="result-card">
          <span className="result-label">Impact</span>
          <p>{String(report.impact ?? "Not established.")}</p>
        </div>
        <div className="result-card">
          <span className="result-label">Recommended change</span>
          <p>{String(report.recommended_change ?? "No change recommended.")}</p>
        </div>
      </div>

      <div className="result-section">
        <div className="result-section-heading">
          <div>
            <span className="result-label">Evidence</span>
            <h4>What the agent actually inspected</h4>
          </div>
          <span className="result-count">{evidenceItems.length} items</span>
        </div>
        <div className="evidence-items">
          {evidenceItems.slice(0, 8).map((item) => (
            <details key={item.id} className="evidence-item">
              <summary>
                <span className="evidence-id">{item.id}</span>
                <span>{item.source}</span>
              </summary>
              <pre>{item.detail}</pre>
            </details>
          ))}
        </div>
      </div>

      <div className="result-section">
        <div className="result-section-heading">
          <div>
            <span className="result-label">Agent execution</span>
            <h4>MCP investigation timeline</h4>
          </div>
          <span className="result-count">{toolCalls.length} calls</span>
        </div>
        <div className="tool-timeline">
          {toolCalls.map((item, index) => {
            const call = (item ?? {}) as Record<string, unknown>;
            return (
              <div className="tool-step" key={String(call.id ?? index)}>
                <span className="tool-step-index">0{index + 1}</span>
                <div>
                  <strong>{String(call.tool ?? "tool")}</strong>
                  <span>{String((call.arguments as Record<string, unknown> | undefined)?.path ?? (call.arguments as Record<string, unknown> | undefined)?.query ?? "repository context")}</span>
                </div>
                <em>{String(call.status ?? "success")}</em>
              </div>
            );
          })}
        </div>
      </div>

      <div className="result-footer">
        <span>Files involved: {Array.isArray(report.files_involved) ? report.files_involved.length : 0}</span>
        <span>Approval: {String(result.approval_status ?? (report.approval_required ? "required" : "not required")).replaceAll("_", " ")}</span>
        <span>Verification: {String(result.verification_status ?? "not started").replaceAll("_", " ")}</span>
        {Boolean(review.decision) && <span>Review: {String(review.decision)}</span>}
        {verification.passed === true && <span className="verified-badge">✓ verified</span>}
      </div>
    </div>
  );
}

export default function Home() {
  const [activeTab, setActiveTab] = useState("overview");
  const [formOpen, setFormOpen] = useState(false);
  const [task, setTask] = useState("Investigate the repository and identify its main components and potential risks.");
  const [repository, setRepository] = useState("sii-1111/Ai-engineering-command-center");
  const [ref, setRef] = useState("main");
  const [submitting, setSubmitting] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const formRef = useRef<HTMLElement>(null);

  function openInvestigation(review = false) {
    if (review) setTask("Review the repository for correctness, security, and maintainability risks.");
    setError("");
    setFormOpen(true);
    window.setTimeout(() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }), 0);
  }

  async function submitInvestigation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setElapsedSeconds(0);
    setError("");
    setResult(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/v1/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task, repository, ref }),
      });
      const data = await response.json();
      if (!response.ok) {
        const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail ?? data);
        throw new Error(detail || `Request failed (${response.status})`);
      }

      setResult(data);
      const taskId = String(data.task_id ?? "");
      if (!taskId) throw new Error("The task API did not return a task ID.");

      const terminalStatuses = new Set([
        "completed",
        "awaiting_approval",
        "rejected",
        "failed",
        "change_failed",
        "verification_failed",
        "verification_passed",
      ]);

      const startedAt = Date.now();
      for (let attempt = 0; attempt < 300; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, attempt === 0 ? 800 : 2000));
        setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));

        const statusResponse = await fetch(`${apiUrl}/v1/tasks/${encodeURIComponent(taskId)}`, {
          cache: "no-store",
        });
        if (statusResponse.status === 404) continue;

        const statusData = await statusResponse.json();
        if (!statusResponse.ok) {
          const detail = typeof statusData.detail === "string"
            ? statusData.detail
            : JSON.stringify(statusData.detail ?? statusData);
          throw new Error(detail || `Task status failed (${statusResponse.status})`);
        }

        setResult(statusData);
        if (terminalStatuses.has(String(statusData.status))) {
          if (statusData.status === "failed" && statusData.error) {
            throw new Error(String(statusData.error));
          }
          break;
        }
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not reach the task API.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <video
        className="art"
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        poster="https://d2ol7oe51mr4n9.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/130837c4-0244-4f37-9c61-8d801d93fd29.jpg"
        src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260912_104303_0c6d60b2-9353-408e-9449-585108a22fb5.mp4"
        aria-hidden="true"
      />

      <div className="veil" />

      <div className="page-shell">
        <header className="bar">
          <a className="brand" href="#overview">
            <svg viewBox="0 0 23 17" aria-hidden="true">
              <path d="M8.15 0.9 L4.55 0.9 L0.5 9.3 L4.1 9.3 Z" />
              <path d="M17.0 0 L13.4 0 L6.15 16.4 L9.75 16.4 Z" />
              <path d="M22.9 0 L19.3 0 L15.0 7.6 L18.6 7.6 Z" />
              <path d="M22.6 6.9 L19.0 6.9 L14.05 16.4 L17.65 16.4 Z" />
            </svg>
            <span id="word">AI CC</span>
          </a>

          <nav className="menu" aria-label="Main navigation">
            {[
              ["overview", "Overview"],
              ["repositories", "Repositories"],
              ["agents", "Agents"],
              ["evidence", "Evidence"],
            ].map(([tab, label]) => (
              <button
                key={tab}
                className={`menu-tab ${activeTab === tab ? "active" : ""}`}
                type="button"
                role="tab"
                aria-selected={activeTab === tab}
                onClick={() => setActiveTab(tab)}
              >
                {label}
              </button>
            ))}
          </nav>

          <button className="pill" type="button" onClick={() => openInvestigation()}>Open workspace</button>
        </header>

        <main className="hero" id="overview">
          <p className="eyebrow">Repository-aware AI engineering</p>

          <h1 className="title">
            <span>AI Engineering</span>
            <span>Command Center</span>
          </h1>

          <p className="sub">
            Investigate real repositories, use tools, verify fixes, and keep risky actions
            under human approval before they ship.
          </p>

          <div className="cta-row">
            <button className="cta" type="button" onClick={() => openInvestigation()}>
              <span>Launch investigation</span>
              <svg className="arrow" viewBox="0 0 16 11" aria-hidden="true">
                <path d="M0 5.5 H14.6 M10.3 1.2 L14.9 5.5 L10.3 9.8" />
              </svg>
            </button>
            <button className="secondary" type="button" onClick={() => openInvestigation(true)}>Review repo</button>
          </div>

          <div className="stats" aria-label="Application status overview">
            {metrics.map((item) => (
              <div key={item.label} className="stat-card">
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </main>

        {formOpen && (
          <section className="task-panel" id="workspace" ref={formRef} aria-labelledby="task-title">
            <div className="panel-header">
              <span className="kicker">New task</span>
              <button className="close-task" type="button" onClick={() => setFormOpen(false)} aria-label="Close task form">×</button>
            </div>
            <h2 id="task-title">Investigate a repository</h2>
            <form className="task-form" onSubmit={submitInvestigation}>
              <label className="field field-wide">
                <span>Engineering task</span>
                <textarea required minLength={1} value={task} onChange={(event) => setTask(event.target.value)} rows={3} />
              </label>
              <label className="field">
                <span>GitHub repository</span>
                <input required pattern="[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+" title="Use owner/repository format" value={repository} onChange={(event) => setRepository(event.target.value)} />
              </label>
              <label className="field">
                <span>Branch or ref</span>
                <input required value={ref} onChange={(event) => setRef(event.target.value)} />
              </label>
              <div className="form-actions">
                <button className="cta" type="submit" disabled={submitting}>
                  <span>{submitting ? "Investigating..." : "Run investigation"}</span>
                  {!submitting && <svg className="arrow" viewBox="0 0 16 11" aria-hidden="true"><path d="M0 5.5 H14.6 M10.3 1.2 L14.9 5.5 L10.3 9.8" /></svg>}
                </button>
                <span className="form-note">
                  {submitting
                    ? `Investigation is running in the background · ${elapsedSeconds}s elapsed`
                    : "The task runs against the configured API and repository."}
                </span>
              </div>
            </form>
            {error && <p className="task-message error" role="alert">{error}</p>}
            {result && (
              <div className="task-result" aria-live="polite">
                <div className="task-result-header">
                  <strong>Task {String(result.status ?? "submitted").replaceAll("_", " ")}</strong>
                  <span>
                    {submitting ? `${elapsedSeconds}s elapsed · ` : ""}
                    {result.task_id ? `ID ${String(result.task_id)}` : ""}
                  </span>
                </div>
                {submitting ? (
                  <div className="task-progress" role="status" aria-live="polite">
                    <span className="progress-spinner" aria-hidden="true" />
                    <div>
                      <strong>Investigation in progress</strong>
                      <p>
                        The agent is inspecting the repository and reasoning over the evidence.
                        The final report will appear automatically when the task completes.
                      </p>
                    </div>
                  </div>
                ) : (
                  <InvestigationResult result={result} />
                )}
              </div>
            )}
          </section>
        )}

        {activeTab !== "overview" && (
          <section className="dashboard" aria-label={`${activeTab} workspace`} role="tabpanel">
            {activeTab === "repositories" && (
              <article className="panel repo-panel">
                <div className="panel-header">
                  <span className="kicker">Repo</span>
                  <span className="live-dot" aria-label="Live repository status" />
                </div>

                <h2>AI Engineering Command Center</h2>

                <div className="repo-meta">
                  <span>main</span>
                  <span>Evidence-backed agent workflows</span>
                </div>

                <ul className="module-list">
                  {repoModules.map((module) => (
                    <li key={module}>
                      <span className="module-name">{module}</span>
                      <span className="module-status success">ready</span>
                    </li>
                  ))}
                </ul>
              </article>
            )}

            {activeTab === "agents" && (
              <article className="panel pipeline-panel">
                <div className="panel-header">
                  <span className="kicker">Workflow</span>
                </div>

                <h2>Investigation pipeline</h2>

                <div className="pipeline-list">
                  {agentFlow.map((step, index) => (
                    <div key={step.title} className="pipeline-step">
                      <span className="step-index">0{index + 1}</span>
                      <div>
                        <strong>{step.title}</strong>
                        <p>{step.text}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            )}

            {activeTab === "evidence" && (
              <article className="panel evidence-panel">
                <div className="panel-header">
                  <span className="kicker">Evidence</span>
                </div>

                <h2>Verification stack</h2>

                <div className="evidence-grid">
                  <div>
                    <span className="label">MCP tools</span>
                    <strong>GitHub + search + repo</strong>
                  </div>
                  <div>
                    <span className="label">Retrieval</span>
                    <strong>Local retrieval + Gemini embeddings</strong>
                  </div>
                  <div>
                    <span className="label">State</span>
                    <strong>Redis + LangGraph</strong>
                  </div>
                  <div>
                    <span className="label">Review</span>
                    <strong>Human approval loop</strong>
                  </div>
                </div>
              </article>
            )}
          </section>
        )}
      </div>

      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@100..900&display=swap');

        :root {
          --bg: #030914;
          --bg-2: #071827;
          --ink: #edf6ff;
          --muted: rgba(208, 224, 241, 0.8);
          --soft: rgba(176, 198, 224, 0.7);
          --line: rgba(191, 212, 235, 0.34);
          --panel: rgba(9, 17, 29, 0.54);
          --panel-strong: rgba(8, 14, 24, 0.7);
          --glow: rgba(134, 193, 255, 0.45);
          --accent: #dfeaf9;
          --accent-strong: #f5f4ff;
          --success: #66f0c1;
          --shadow: rgba(3, 8, 15, 0.7);
        }

        * { box-sizing: border-box; }

        html, body {
          margin: 0;
          min-height: 100%;
          background: var(--bg);
          color: var(--ink);
          font-family: 'Sora', sans-serif;
        }

        body {
          min-height: 100vh;
          background:
            radial-gradient(circle at 50% 20%, rgba(113, 164, 232, 0.18), transparent 32%),
            linear-gradient(180deg, var(--bg) 0%, var(--bg-2) 100%);
        }

        a { color: inherit; text-decoration: none; }
        button { color: inherit; font: inherit; cursor: pointer; }
        ul { list-style: none; margin: 0; padding: 0; }

        .art {
          position: fixed;
          inset: 0;
          width: 100%;
          height: 100%;
          object-fit: cover;
          object-position: center;
          z-index: 0;
          opacity: 0.8;
          filter: saturate(0.9) contrast(1.12) brightness(0.7);
          pointer-events: none;
        }

        .veil {
          position: fixed;
          inset: 0;
          z-index: 0;
          background:
            radial-gradient(140% 60% at 50% 42%, rgba(8, 15, 22, 0.08), rgba(3, 9, 20, 0.28) 38%, rgba(3, 9, 20, 0.8) 100%),
            linear-gradient(180deg, rgba(2, 6, 12, 0.1), rgba(2, 6, 12, 0.7));
          pointer-events: none;
        }

        .page-shell {
          position: relative;
          z-index: 1;
          width: min(1400px, calc(100vw - 48px));
          margin: 0 auto;
          padding: 30px 0 70px;
        }

        .bar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 24px;
          min-height: 86px;
        }

        .brand {
          display: inline-flex;
          align-items: center;
          gap: 14px;
          font-size: 2.2rem;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          font-weight: 700;
        }

        .brand svg {
          width: 30px;
          height: 22px;
          fill: var(--ink);
          opacity: 0.95;
        }

        .menu {
          display: flex;
          align-items: center;
          gap: 36px;
          margin-left: auto;
          margin-right: 26px;
          font-size: 0.82rem;
          color: var(--muted);
        }

        .menu-tab {
          position: relative;
          border: 0;
          padding: 4px 0;
          background: transparent;
          color: var(--muted);
          font: inherit;
          font-size: 0.82rem;
          transition: color 0.2s ease;
        }

        .menu-tab::after {
          content: "";
          position: absolute;
          left: 0;
          right: 0;
          bottom: -8px;
          height: 1px;
          background: rgba(197, 216, 239, 0.8);
          transform: scaleX(0);
          transform-origin: center;
          transition: transform 0.2s ease;
        }

        .menu-tab:hover,
        .menu-tab.active,
        .menu-tab:focus-visible { color: var(--ink); }

        .menu-tab:hover::after,
        .menu-tab.active::after,
        .menu-tab:focus-visible::after { transform: scaleX(1); }

        .pill {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 180px;
          min-height: 46px;
          border-radius: 999px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.06);
          backdrop-filter: blur(14px);
          -webkit-backdrop-filter: blur(14px);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 0 24px rgba(111, 170, 255, 0.12);
          font-size: 0.82rem;
          letter-spacing: 0.02em;
        }

        .hero {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding-top: 72px;
        }

        .task-panel {
          width: min(900px, 100%);
          margin: 42px auto 0;
          padding: 24px;
          border: 1px solid rgba(194, 215, 240, 0.2);
          border-radius: 18px;
          background: rgba(7, 14, 23, 0.78);
          box-shadow: 0 18px 48px rgba(2, 6, 12, 0.34);
          backdrop-filter: blur(18px);
          -webkit-backdrop-filter: blur(18px);
        }

        .task-panel h2 {
          margin: 0 0 20px;
          font-size: 1.5rem;
        }

        .close-task {
          width: 34px;
          height: 34px;
          border: 1px solid var(--line);
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.06);
          font-size: 1.3rem;
          line-height: 1;
        }

        .task-form {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
        }

        .field {
          display: flex;
          flex-direction: column;
          gap: 8px;
          min-width: 0;
          color: var(--muted);
          font-size: 0.78rem;
        }

        .field-wide,
        .form-actions { grid-column: 1 / -1; }

        .field input,
        .field textarea {
          width: 100%;
          border: 1px solid rgba(194, 215, 240, 0.24);
          border-radius: 8px;
          padding: 12px 14px;
          background: rgba(1, 7, 13, 0.62);
          color: var(--ink);
          font: inherit;
          font-size: 0.9rem;
          resize: vertical;
        }

        .field input:focus-visible,
        .field textarea:focus-visible,
        button:focus-visible {
          outline: 2px solid var(--success);
          outline-offset: 3px;
        }

        .form-actions {
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          gap: 14px;
        }

        .form-actions .cta { min-height: 48px; }
        .cta:disabled { cursor: wait; opacity: 0.65; }

        .form-note,
        .task-result > div span {
          color: var(--soft);
          font-size: 0.76rem;
        }

        .task-message {
          margin: 18px 0 0;
          padding: 12px 14px;
          border-radius: 8px;
          line-height: 1.5;
        }

        .task-message.error {
          border: 1px solid rgba(255, 142, 142, 0.4);
          background: rgba(128, 30, 36, 0.22);
          color: #ffd4d4;
        }

        .investigation-result {
          min-width: 920px;
          padding: 18px;
        }

        .task-result-header {
          display: flex;
          justify-content: space-between;
          gap: 14px;
          padding: 12px 14px;
          border-bottom: 1px solid rgba(194, 215, 240, 0.14);
        }

        .result-summary {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
          margin-bottom: 18px;
        }

        .result-kicker,
        .result-label {
          display: block;
          color: rgba(200, 221, 242, 0.68);
          font-size: 0.67rem;
          letter-spacing: 0.14em;
          text-transform: uppercase;
        }

        .result-summary h3 {
          margin: 6px 0 0;
          font-size: 1.25rem;
          text-transform: capitalize;
        }

        .confidence-ring {
          min-width: 78px;
          min-height: 78px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          border: 1px solid rgba(102, 240, 193, 0.3);
          border-radius: 50%;
          background: rgba(102, 240, 193, 0.06);
        }

        .confidence-ring strong { font-size: 1.1rem; }
        .confidence-ring span { font-size: 0.55rem; color: var(--soft); }

        .result-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }

        .result-card {
          padding: 16px;
          border: 1px solid rgba(194, 215, 240, 0.12);
          border-radius: 12px;
          background: rgba(255,255,255,0.018);
        }

        .result-card-wide { grid-column: 1 / -1; }
        .result-card p { margin: 8px 0 0; color: var(--muted); line-height: 1.55; font-size: 0.82rem; }

        .result-section { margin-top: 22px; }

        .result-section-heading {
          display: flex;
          align-items: end;
          justify-content: space-between;
          gap: 14px;
          margin-bottom: 10px;
        }

        .result-section-heading h4 { margin: 5px 0 0; font-size: 0.98rem; }
        .result-count { color: var(--soft); font-size: 0.68rem; }

        .evidence-items,
        .tool-timeline {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .evidence-item {
          border: 1px solid rgba(194, 215, 240, 0.1);
          border-radius: 10px;
          background: rgba(255,255,255,0.015);
          overflow: hidden;
        }

        .evidence-item summary {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 11px 12px;
          cursor: pointer;
          list-style: none;
          color: var(--muted);
          font-size: 0.72rem;
        }

        .evidence-id {
          padding: 4px 7px;
          border-radius: 6px;
          background: rgba(145, 188, 255, 0.1);
          color: var(--accent);
          font-size: 0.62rem;
        }

        .evidence-item pre {
          max-height: 220px;
          overflow: auto;
          margin: 0;
          padding: 12px;
          border-top: 1px solid rgba(194, 215, 240, 0.08);
          color: #cbddec;
          font-size: 0.67rem;
          line-height: 1.5;
          white-space: pre-wrap;
          overflow-wrap: anywhere;
        }

        .tool-step {
          display: grid;
          grid-template-columns: 34px 1fr auto;
          align-items: center;
          gap: 10px;
          padding: 10px;
          border: 1px solid rgba(194, 215, 240, 0.1);
          border-radius: 10px;
          background: rgba(255,255,255,0.015);
        }

        .tool-step-index {
          display: grid;
          place-items: center;
          width: 30px;
          height: 30px;
          border-radius: 9px;
          background: rgba(102, 240, 193, 0.1);
          color: #bfffe9;
          font-size: 0.62rem;
          font-weight: 700;
        }

        .tool-step strong,
        .tool-step span {
          display: block;
        }

        .tool-step strong { font-size: 0.76rem; }
        .tool-step span { margin-top: 3px; color: var(--soft); font-size: 0.63rem; }
        .tool-step em { color: #bfffe9; font-size: 0.62rem; font-style: normal; text-transform: uppercase; }

        .result-footer {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 18px;
        }

        .result-footer span {
          padding: 7px 9px;
          border-radius: 999px;
          border: 1px solid rgba(194, 215, 240, 0.1);
          color: var(--soft);
          font-size: 0.63rem;
        }

        .result-footer .verified-badge {
          color: #bfffe9;
          border-color: rgba(102, 240, 193, 0.25);
          background: rgba(102, 240, 193, 0.08);
        }

        .task-result {
          margin-top: 20px;
          max-height: min(70vh, 760px);
          overflow-x: auto;
          overflow-y: auto;
          scrollbar-gutter: stable both-edges;
          border: 1px solid rgba(194, 215, 240, 0.18);
          border-radius: 10px;
          background: rgba(1, 7, 13, 0.58);
        }

        .task-result::-webkit-scrollbar {
          width: 10px;
          height: 10px;
        }

        .task-result::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.025);
          border-radius: 999px;
        }

        .task-result::-webkit-scrollbar-thumb {
          background: rgba(194, 215, 240, 0.32);
          border: 2px solid rgba(1, 7, 13, 0.58);
          border-radius: 999px;
        }

        .task-result::-webkit-scrollbar-thumb:hover {
          background: rgba(194, 215, 240, 0.52);
        }

        .task-result::-webkit-scrollbar-corner {
          background: rgba(1, 7, 13, 0.58);
        }

        .task-progress {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 28px 20px;
          border-bottom: 1px solid rgba(194, 215, 240, 0.12);
        }

        .task-progress strong {
          display: block;
          font-size: 0.86rem;
        }

        .task-progress p {
          margin: 5px 0 0;
          color: var(--soft);
          font-size: 0.72rem;
          line-height: 1.5;
        }

        .progress-spinner {
          width: 28px;
          height: 28px;
          flex: 0 0 auto;
          border: 2px solid rgba(194, 215, 240, 0.18);
          border-top-color: var(--success);
          border-radius: 50%;
          animation: task-spin 0.9s linear infinite;
        }

        @keyframes task-spin {
          to { transform: rotate(360deg); }
        }

        .task-result > div {
          display: flex;
          justify-content: space-between;
          gap: 14px;
          padding: 12px 14px;
          border-bottom: 1px solid rgba(194, 215, 240, 0.14);
        }

        .task-result pre {
          max-height: 320px;
          overflow: auto;
          margin: 0;
          padding: 14px;
          color: #d1e3f2;
          font-size: 0.76rem;
          line-height: 1.5;
          white-space: pre-wrap;
          overflow-wrap: anywhere;
        }

        .eyebrow {
          margin: 0 0 22px;
          font-size: 0.77rem;
          letter-spacing: 0.22em;
          text-transform: uppercase;
          color: rgba(213, 232, 255, 0.74);
        }

        .title {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin: 0;
          font-size: clamp(3.3rem, 5vw, 6.2rem);
          line-height: 0.96;
          letter-spacing: -0.06em;
          font-weight: 700;
        }

        .sub {
          margin: 30px 0 0;
          max-width: 760px;
          color: var(--muted);
          font-size: clamp(1.1rem, 1.8vw, 1.7rem);
          line-height: 1.55;
          letter-spacing: -0.03em;
        }

        .cta-row {
          display: flex;
          flex-wrap: wrap;
          justify-content: center;
          gap: 18px;
          margin-top: 42px;
        }

        .cta,
        .secondary {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 14px;
          min-height: 62px;
          border-radius: 999px;
          padding: 0 28px;
          font-weight: 600;
          letter-spacing: -0.03em;
        }

        .cta {
          background: linear-gradient(180deg, rgba(255,255,255,0.18), rgba(255,255,255,0.06));
          border: 1px solid rgba(255,255,255,0.22);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.26), 0 0 36px rgba(131, 174, 255, 0.14);
        }

        .secondary {
          border: 1px solid rgba(191, 212, 235, 0.24);
          background: rgba(7, 12, 18, 0.2);
          color: var(--accent);
        }

        .arrow {
          width: 18px;
          height: 12px;
          stroke: var(--ink);
          stroke-width: 1.8;
          fill: none;
          stroke-linecap: round;
          stroke-linejoin: round;
        }

        .stats {
          display: grid;
          grid-template-columns: repeat(4, minmax(140px, 1fr));
          gap: 18px;
          width: min(900px, 100%);
          margin-top: 46px;
        }

        .stat-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          padding: 20px 14px 18px;
          border: 1px solid rgba(194, 215, 240, 0.18);
          border-radius: 18px;
          background: rgba(12, 23, 33, 0.38);
          box-shadow: 0 10px 30px rgba(6, 11, 18, 0.18);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
        }

        .stat-card span {
          font-size: 0.68rem;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          color: rgba(208, 223, 238, 0.8);
        }

        .stat-card strong {
          font-size: clamp(1.2rem, 1.5vw, 1.9rem);
          letter-spacing: -0.06em;
        }

        .dashboard {
          display: grid;
          grid-template-columns: 1.12fr 1.28fr 0.9fr;
          gap: 22px;
          margin-top: 72px;
        }

        .panel {
          background: rgba(9, 16, 28, 0.56);
          border: 1px solid rgba(194, 215, 240, 0.17);
          border-radius: 22px;
          padding: 22px 20px 20px;
          box-shadow: 0 12px 34px rgba(2, 6, 12, 0.25);
          backdrop-filter: blur(18px);
          -webkit-backdrop-filter: blur(18px);
        }

        .panel-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 18px;
        }

        .kicker {
          display: inline-block;
          color: rgba(200, 221, 242, 0.78);
          font-size: 0.72rem;
          letter-spacing: 0.18em;
          text-transform: uppercase;
        }

        .live-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: var(--success);
          box-shadow: 0 0 14px rgba(102, 240, 193, 0.9);
        }

        .panel h2 {
          margin: 0 0 16px;
          font-size: clamp(1.4rem, 2.2vw, 2rem);
          letter-spacing: -0.05em;
        }

        .repo-meta {
          display: flex;
          justify-content: space-between;
          gap: 16px;
          padding: 12px 14px;
          margin-bottom: 18px;
          border-radius: 12px;
          background: rgba(255,255,255,0.02);
          border: 1px solid rgba(215, 232, 252, 0.08);
          color: var(--muted);
          font-size: 0.82rem;
        }

        .module-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .module-list li {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 12px 12px;
          border-radius: 12px;
          background: rgba(255,255,255,0.015);
          border: 1px solid rgba(200, 220, 242, 0.06);
        }

        .module-name {
          font-weight: 500;
          letter-spacing: -0.02em;
        }

        .module-status {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          padding: 6px 10px;
          border-radius: 999px;
          font-size: 0.7rem;
          letter-spacing: 0.12em;
          text-transform: uppercase;
        }

        .module-status.success {
          background: rgba(102, 240, 193, 0.12);
          color: #bfffe9;
        }

        .pipeline-list {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }

        .pipeline-step {
          display: flex;
          align-items: flex-start;
          gap: 14px;
          padding: 12px 10px;
          border-radius: 12px;
          border: 1px solid rgba(201, 219, 235, 0.08);
          background: rgba(255,255,255,0.012);
        }

        .step-index {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 38px;
          height: 38px;
          border-radius: 12px;
          background: rgba(145, 188, 255, 0.1);
          color: var(--accent-strong);
          font-size: 0.7rem;
          font-weight: 700;
        }

        .pipeline-step strong {
          display: block;
          margin-bottom: 6px;
          font-size: 0.98rem;
        }

        .pipeline-step p {
          margin: 0;
          color: var(--muted);
          font-size: 0.82rem;
          line-height: 1.5;
        }

        .evidence-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
        }

        .evidence-grid > div {
          display: flex;
          flex-direction: column;
          gap: 8px;
          border-radius: 14px;
          background: rgba(255,255,255,0.02);
          border: 1px solid rgba(201, 219, 235, 0.08);
          padding: 16px 14px;
        }

        .label {
          color: rgba(206, 221, 240, 0.76);
          font-size: 0.7rem;
          letter-spacing: 0.12em;
          text-transform: uppercase;
        }

        .evidence-grid strong {
          font-size: 0.96rem;
          line-height: 1.3;
        }

        @media (max-width: 1050px) {
          .page-shell {
            width: min(1100px, calc(100vw - 32px));
          }

          .dashboard {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 760px) {
          .page-shell {
            width: min(680px, calc(100vw - 22px));
            padding-top: 18px;
          }

          .bar {
            flex-wrap: wrap;
            justify-content: center;
            gap: 14px;
          }

          .brand { font-size: 1.5rem; }
          .menu {
            order: 3;
            width: 100%;
            justify-content: center;
            margin: 0;
            gap: 18px;
            flex-wrap: wrap;
          }

          .stats {
            grid-template-columns: repeat(2, minmax(120px, 1fr));
          }

          .hero {
            padding-top: 44px;
          }

          .task-panel { padding: 18px 14px; }
          .task-form { grid-template-columns: 1fr; }
          .field-wide,
          .form-actions { grid-column: auto; }

          .sub {
            max-width: 560px;
          }
        }

        @media (prefers-reduced-motion: reduce) {
          * {
            animation: none !important;
            transition: none !important;
            scroll-behavior: auto !important;
          }
        }
      `}</style>
    </>
  );
}
