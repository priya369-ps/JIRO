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
  const [status, setStatus] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!resume.trim() || !jobDescription.trim()) {
      setError("Add both a resume and a job description before continuing.");
      setStatus("");
      return;
    }
    setLoading(true); setError(""); setResult(null);
    setStatus("Analyzing the source documents.");
    try {
      const tailoringResult = await tailor(resume, jobDescription, provider as Provider);
      setResult(tailoringResult);
      setStatus(tailoringResult.validation.export_blocked ? "Review required. Export is blocked until the warnings are resolved." : "Analysis complete. Review the matches, gaps, and output.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Request failed safely.");
      setStatus("Analysis failed.");
    } finally { setLoading(false); }
  }

  const canSubmit = Boolean(resume.trim() && jobDescription.trim()) && !loading;
  return (
    <main className="shell">
      <header className="topbar">
        <div><span className="kicker">JIRO / EVIDENCE-LED TAILORING</span><h1>Make the fit visible.</h1></div>
        <div className="privacy"><span className="status-dot" /> Ephemeral mode<br /><small>No documents are stored</small></div>
      </header>
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">{status}</div>
      <section className="intro"><p>Shape a resume around a role without crossing the line between reframing and invention.</p><span>01 INPUT</span><span>02 REVIEW</span><span>03 EXPORT</span></section>
      <form className="workspace" onSubmit={submit}>
        <section className="panel document-panel">
          <div className="panel-heading"><div><span className="eyebrow">SOURCE MATERIAL</span><h2>Bring the evidence.</h2></div><span className="step">01</span></div>
          <div className="field"><label htmlFor="resume">Resume</label><textarea id="resume" aria-describedby="resume-help" aria-invalid={Boolean(error && !resume.trim())} value={resume} onChange={event => setResume(event.target.value)} placeholder="Paste the candidate resume here..." /><div className="field-foot"><span id="resume-help">{resume.length} characters; source facts are retained in memory only.</span><label className="upload">Add file<input className="sr-only" type="file" accept=".txt,.pdf,.docx,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={event => void readFile(event, provider as Provider, setResume, setError)} /></label></div></div>
          <div className="field"><label htmlFor="job">Job description</label><textarea id="job" aria-describedby="job-help" aria-invalid={Boolean(error && !jobDescription.trim())} value={jobDescription} onChange={event => setJobDescription(event.target.value)} placeholder="Paste the target role here..." /><div className="field-foot"><span id="job-help">{jobDescription.length} characters; requirements are compared with the source resume.</span><label className="upload">Add file<input className="sr-only" type="file" accept=".txt,.pdf,.docx,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={event => void readFile(event, provider as Provider, setJobDescription, setError)} /></label></div></div>
          <div className="config-row"><label htmlFor="provider">Provider</label><select id="provider" value={provider} onChange={event => setProvider(event.target.value)}><option value="groq">Shared Groq</option><option value="byok">Bring your key</option><option value="local">Local model</option></select><span className="config-note">Configured by the backend</span></div>
          <button className="primary" type="submit" aria-busy={loading} disabled={!canSubmit}>{loading ? "Analyzing..." : "Analyze and tailor"}<span aria-hidden="true">→</span></button>
          {error && <div className="error" role="alert" aria-live="assertive">{error}</div>}
        </section>
        <aside className="panel guidance"><span className="eyebrow">GUARDRAILS</span><h2>Source facts stay sacred.</h2><p>JIRO can reorder, clarify, and align language that already exists in the resume. Missing requirements stay visible as gaps.</p><div className="rule-list"><div><b>✓</b><span>Matches show evidence lines.</span></div><div><b>△</b><span>Gaps are never filled by invention.</span></div><div><b>!</b><span>Warnings appear before export.</span></div></div></aside>
      </form>
      {result && <Review result={result} />}
    </main>
  );
}

function Review({ result }: { result: TailoringResponse }) {
  return <section className="review" aria-labelledby="review-title"><div className="review-header"><div><span className="eyebrow">REVIEW / {result.workflow.state.toUpperCase()}</span><h2 id="review-title">See what the evidence supports.</h2></div><span className={`validation ${result.validation.status}`}>{result.validation.status === "passed" ? "Validated" : "Review required"}</span></div><div className="review-grid"><div><h3>Matches <span aria-label={`${result.matches.length} matches`}>{result.matches.length}</span></h3>{result.matches.length ? result.matches.map(item => <div className="requirement match" key={item.value}><b>{item.value}</b><small>{item.evidence}</small></div>) : <p className="muted">No direct matches yet.</p>}</div><div><h3>Gaps <span aria-label={`${result.gaps.length} gaps`}>{result.gaps.length}</span></h3>{result.gaps.length ? result.gaps.map(item => <div className="requirement gap" key={item.value}><b>{item.value}</b><small>Not found in the source resume</small></div>) : <p className="muted">No gaps detected.</p>}</div><div className="output"><h3>Tailored output</h3><pre aria-label="Tailored resume output">{result.tailored_resume}</pre></div></div><div className="review-footer"><div className="warning-panel" role="region" aria-labelledby="warnings-title"><h3 id="warnings-title">Warnings</h3>{result.validation.warnings.length ? result.validation.warnings.map(warning => <p key={warning}>{warning}</p>) : <p className="muted">No validation warnings.</p>}</div><div className="exports" role="region" aria-labelledby="exports-title"><h3 id="exports-title">Export</h3>{result.validation.export_blocked && <div className="export-blocked" role="alert"><strong>Export blocked.</strong> Resolve the validation warnings before downloading this resume.</div>}{result.exports.map(item => <span className={item.available ? "export available" : "export"} key={item.format}>{item.format} <span>{item.available ? "ready" : item.reason ?? "deferred"}</span></span>)}</div></div><div className="diff-panel" role="region" aria-labelledby="diff-title"><h3 id="diff-title">What changed</h3><p className="muted">{result.diff.summary}</p><pre aria-label="Accessible resume diff">{result.diff.unified ? result.diff.unified.split("\n").map((line, index) => <span className={line.startsWith("+") && !line.startsWith("+++") ? "diff-add" : line.startsWith("-") && !line.startsWith("---") ? "diff-remove" : "diff-context"} key={`${index}-${line}`}><span className="sr-only">{line.startsWith("+") && !line.startsWith("+++") ? "Added: " : line.startsWith("-") && !line.startsWith("---") ? "Removed: " : ""}</span>{line}{"\n"}</span>) : <span className="muted">No changes.</span>}</pre></div></section>;
}
