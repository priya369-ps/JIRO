# JIRO

The implementation guide is available in a chunked format:

- [JIRO Build Guide, Chunked Edition](JIRO_BUILD_GUIDE_CHUNKS.md)
- [Canonical Agent Build Guide](AGENTS.md)

## Chunk 01 Implementation

The first implementation slice establishes the JIRO mission contract as a minimal FastAPI service.

Run the service with:


## Chunk 15 Implementation

The implementation order is now executable through [app/config.py](app/config.py)
and the existing FastAPI health check. Runtime configuration is loaded from
environment variables without reading API keys into the settings object:

- `JIRO_DEFAULT_PROVIDER` defaults to `groq`.
- `JIRO_GROQ_MODEL` defaults to `openai/gpt-oss-120b`.
- `JIRO_OLLAMA_ENDPOINT` defaults to `http://localhost:11434`.
- `JIRO_PROVIDER_TIMEOUT_SECONDS` is validated and capped at 120 seconds.

The service exposes only non-secret configuration metadata from `/health`. The
repository uses the text-first FastAPI MVP, direct provider adapters, and the
existing deterministic pipeline before adding history, authentication, or
deferred exporters.

## Chunk 16 Implementation

The acceptance matrix is covered by the repository test suite and
[tests/test_acceptance.py](tests/test_acceptance.py). It verifies malformed and
oversized files, empty and unsupported inputs, provider timeouts, invalid
configuration, unsupported claims, export blocking, rate limits, provider
fakes, secret-free metadata, parsing, matching, prompt safety, and export
behavior. Tests inject transports and pipeline stages, so they never require
live credentials or network access.

Run the complete deterministic gate with:

```bash
python -m unittest discover -s tests -v
```
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

## Chunk 11 Implementation

The processing pipeline is composed of explicit, injectable stages: input
parsing, job-description analysis, resume matching, rewriting, claim
validation, formatting, and export. The current defaults are deterministic and
source-preserving, while tests can replace any stage with a fake implementation
without making a model call. Validation runs before export, and failed
validation blocks export results while retaining the warnings.

## Chunk 12 Implementation

Privacy controls are implemented in [app/privacy.py](app/privacy.py) and are
applied at ingestion and provider boundaries. Filenames reject paths, hidden
names, control characters, traversal names, and excessive lengths. Text and
file limits remain enforced, and source documents are held only in the request
pipeline; JIRO does not add persistence or write uploaded content to disk.

Provider options are filtered so secret-like keys cannot enter outbound model
payloads. Diagnostic mappings can be redacted, API keys remain excluded from
response metadata, and parser/provider errors contain safe messages without
echoing resume, job-description, file, or credential content. Extracted text
and model output continue to be treated as untrusted input for later stages.

## Chunk 13 Implementation

The API applies an explicit request-body limit, restrictive CORS defaults, and
bounded timeout validation. Uploaded content is read with a one-byte overflow
allowance so oversized files are rejected without unbounded buffering. The
provider layer continues to use bounded per-session rate limiting and safe
provider errors without logging source text or secrets.

## Chunk 14 Implementation

Input and tailoring responses expose workflow metadata for frontend states:
`input` and `review`, with validation status, warnings, export availability,
and an explicit `ephemeral` privacy mode. No workflow history or resume content
is persisted; processing state can be represented by the frontend while a
request is in flight, and blocked exports remain visible in the review state.