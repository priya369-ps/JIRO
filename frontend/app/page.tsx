"use client";

import { ChangeEvent, FormEvent, useState } from "react";
import { ingestFile, tailor, TailoringResponse, Provider } from "../lib/api";

async function readFile(event: ChangeEvent<HTMLInputElement>, provider: Provider, setter: (value: string) => void, onError: (message: string) => void) {
  const file = event.target.files?.[0];
  if (!file) return;
  try { setter((await ingestFile(file, provider)).normalized_text); }
  catch (error) { onError(error instanceof Error ? error.message : "File ingestion failed safely."); }
}

export default function Home() {
  const [resume, setResume] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [provider, setProvider] = useState("groq");
  const [result, setResult] = useState<TailoringResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!resume.trim() || !jobDescription.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try { setResult(await tailor(resume, jobDescription, provider as Provider)); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Request failed safely."); }
    finally { setLoading(false); }
  }

  const canSubmit = Boolean(resume.trim() && jobDescription.trim()) && !loading;
  return (
    <main className="shell">
      <header className="topbar">
        <div><span className="kicker">JIRO / EVIDENCE-LED TAILORING</span><h1>Make the fit visible.</h1></div>
        <div className="privacy"><span className="status-dot" /> Ephemeral mode<br /><small>No documents are stored</small></div>
      </header>
      <section className="intro"><p>Shape a resume around a role without crossing the line between reframing and invention.</p><span>01 INPUT</span><span>02 REVIEW</span><span>03 EXPORT</span></section>
      <form className="workspace" onSubmit={submit}>
        <section className="panel document-panel">
          <div className="panel-heading"><div><span className="eyebrow">SOURCE MATERIAL</span><h2>Bring the evidence.</h2></div><span className="step">01</span></div>
          <div className="field"><label htmlFor="resume">Resume</label><textarea id="resume" value={resume} onChange={event => setResume(event.target.value)} placeholder="Paste the candidate resume here..." /><div className="field-foot"><span>{resume.length} characters</span><label className="upload">Add file<input type="file" accept=".txt,.pdf,.docx,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={event => void readFile(event, provider as Provider, setResume, setError)} /></label></div></div>
          <div className="field"><label htmlFor="job">Job description</label><textarea id="job" value={jobDescription} onChange={event => setJobDescription(event.target.value)} placeholder="Paste the target role here..." /><div className="field-foot"><span>{jobDescription.length} characters</span><label className="upload">Add file<input type="file" accept=".txt,.pdf,.docx,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={event => void readFile(event, provider as Provider, setJobDescription, setError)} /></label></div></div>
          <div className="config-row"><label htmlFor="provider">Provider</label><select id="provider" value={provider} onChange={event => setProvider(event.target.value)}><option value="groq">Shared Groq</option><option value="byok">Bring your key</option><option value="local">Local model</option></select><span className="config-note">Configured by the backend</span></div>
          <button className="primary" disabled={!canSubmit}>{loading ? "Analyzing..." : "Analyze and tailor"}<span>→</span></button>
          {error && <div className="error" role="alert">{error}</div>}
        </section>
        <aside className="panel guidance"><span className="eyebrow">GUARDRAILS</span><h2>Source facts stay sacred.</h2><p>JIRO can reorder, clarify, and align language that already exists in the resume. Missing requirements stay visible as gaps.</p><div className="rule-list"><div><b>✓</b><span>Matches show evidence lines.</span></div><div><b>△</b><span>Gaps are never filled by invention.</span></div><div><b>!</b><span>Warnings appear before export.</span></div></div></aside>
      </form>
      {result && <Review result={result} />}
    </main>
  );
}

function Review({ result }: { result: TailoringResponse }) {
  return <section className="review"><div className="review-header"><div><span className="eyebrow">REVIEW / {result.workflow.state.toUpperCase()}</span><h2>See what the evidence supports.</h2></div><span className={`validation ${result.validation.status}`}>{result.validation.status === "passed" ? "Validated" : "Review required"}</span></div><div className="review-grid"><div><h3>Matches <span>{result.matches.length}</span></h3>{result.matches.length ? result.matches.map(item => <div className="requirement match" key={item.value}><b>{item.value}</b><small>{item.evidence}</small></div>) : <p className="muted">No direct matches yet.</p>}</div><div><h3>Gaps <span>{result.gaps.length}</span></h3>{result.gaps.length ? result.gaps.map(item => <div className="requirement gap" key={item.value}><b>{item.value}</b><small>Not found in the source resume</small></div>) : <p className="muted">No gaps detected.</p>}</div><div className="output"><h3>Tailored output</h3><pre>{result.tailored_resume}</pre></div></div><div className="review-footer"><div><h3>Warnings</h3>{result.validation.warnings.map(warning => <p key={warning}>{warning}</p>)}</div><div className="exports"><h3>Export</h3>{result.exports.map(item => <span className={item.available ? "export available" : "export"} key={item.format}>{item.format} {item.available ? "ready" : "deferred"}</span>)}</div></div></section>;
}
