# JIRO

The implementation guide is available in a chunked format:

- [JIRO Build Guide, Chunked Edition](JIRO_BUILD_GUIDE_CHUNKS.md)
- [Canonical Agent Build Guide](AGENTS.md)

## Chunk 01 Implementation

The first implementation slice establishes the JIRO mission contract as a minimal FastAPI service.

Run the service with:

```bash
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/health` to inspect the service status, pipeline stages, and no-fabrication policy.

Run the focused test without extra tooling:

```bash
python -m unittest discover -s tests -v
```

## Chunk 02 Implementation

Chunk 2 establishes the operating contract for AI coding agents. Before changing
the application, agents must read [AGENTS.md](AGENTS.md) and follow its rules for
scope, module boundaries, privacy, secrets, failure handling, testing, and
validation.

This chunk does not add runtime product behavior. Its implementation is the
canonical repository-level guide and its required decision rules. Later chunks
must preserve those rules rather than reimplementing them in individual
features.

## Chunk 03 Implementation

The input boundary accepts pasted text and PDF, DOCX, or UTF-8 TXT files. Each
input is converted to an `IngestedDocument` containing both the original text
and a normalized text representation. Inputs larger than 5 MB, empty inputs,
unsafe filenames, and unsupported file types are rejected.

The API endpoints are `POST /ingest/text` and `POST /ingest/file`. The file
endpoint extracts PDF and DOCX content using `pdfplumber` and `python-docx`.

## Chunk 04 Implementation

The output boundary is exposed through `POST /tailor`. It returns a structured
tailoring result containing the source-preserving tailored resume, extracted job
requirements, matched requirements, gaps, validation status and warnings, a
machine-readable unified diff with a human-readable summary, and export
metadata.

Markdown export is available in this milestone. DOCX and PDF are returned as
explicitly unavailable rather than silently producing incomplete files; their
renderers belong to later export milestones. The current deterministic output
service does not invent a rewrite, so the tailored resume remains the
normalized source resume until the model and rewrite stages are implemented.

## Chunk 05 Implementation

The tailoring result reports ATS risks detected in text input, including
tab-separated columns, table-like content, and image markers. Source-supported
job terms remain matches, unsupported terms remain gaps, and the deterministic
MVP never inserts missing keywords or rewrites unsupported facts. A model-backed
rewrite stage can later tailor supported summary, experience, and skills text
behind the same result contract.

## Chunk 06 Implementation

The application now follows explicit architecture boundaries in
[app/architecture.py](app/architecture.py). The contracts separate input
parsing, job analysis, resume matching, rewriting, claim validation, export
rendering, model access, and pipeline orchestration.

[app/pipeline.py](app/pipeline.py) owns the current dependency wiring. The
FastAPI layer delegates ingestion to `DefaultInputParser` and tailoring to
`DeterministicTailoringPipeline`; it does not contain provider-specific logic
or pipeline implementation details. The deterministic pipeline preserves the
current no-fabrication behavior while leaving model-provider implementations
for later chunks.

## Chunk 07 Implementation

JIRO uses FastAPI for the backend and keeps the current MVP text-first, with no
frontend framework introduced yet. PDF and DOCX ingestion use `pdfplumber` and
`python-docx`, respectively; TXT input is handled by the standard library.
Markdown is the currently implemented export format.

The future full product frontend is planned as Next.js. It will be introduced
as a separate frontend once the backend workflow and provider contract are
ready; Streamlit is intentionally not added alongside it. Future model access
will use direct provider SDKs behind the provider-neutral interface, without
adding an orchestration framework before a real multi-step workflow requires
one. DOCX and PDF export dependencies likewise remain deferred until their
export milestone.

## Chunk 08 Implementation

The provider contract is implemented in
[app/model_provider.py](app/model_provider.py). `ModelProvider` exposes the
single `generate(prompt, config) -> ModelResponse` boundary, while
`ModelConfig` carries provider-neutral model settings. `ModelResponse` retains
safe diagnostic metadata including provider, model, request ID, token counts,
and finish status without exposing API keys.

The contract validates provider names, model names, prompts, and token counts.
Provider implementations are intentionally deferred to Chunk 9; tests use a
fake provider and never require live credentials.

## Chunk 09 Implementation

Provider adapters now live behind the same `ModelProvider` contract in
[app/model_provider.py](app/model_provider.py). The default `GroqProvider`
uses `GROQ_API_KEY` from server-side environment configuration, defaults to
`openai/gpt-oss-120b`, and applies a bounded per-session rate limit. It never
falls back silently when configuration or the provider request fails.

`BYOKProvider` accepts a per-request key and supports Groq, OpenAI, and
Anthropic upstream configuration without persisting or exposing the key.
`LocalProvider` defaults to an Ollama-compatible local endpoint and does not
use the shared Groq key or fall back to another provider. Provider failures are
returned as safe configuration or request errors, while tests use an injected
transport and do not make live network calls.

## Chunk 10 Implementation

Prompt and claim safety is implemented in [app/safety.py](app/safety.py). The
rewrite prompt identifies the source resume as the only authority for candidate
facts, treats missing job-description requirements as gaps, prohibits invented
companies, titles, dates, skills, responsibilities, achievements, and metrics,
and requests a structured response schema.

`DeterministicClaimValidator` compares generated text with the source resume and
flags unsupported dates, metrics, companies, titles, known technical skills,
and responsibility statements. Failed validation is marked untrusted and blocks
export through `ValidationResult.export_blocked`; warnings remain attached for
review. Tests use deterministic text and do not require a model call.