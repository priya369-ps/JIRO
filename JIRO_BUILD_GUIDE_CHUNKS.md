# JIRO Build Guide, Chunked Edition

This document divides the JIRO agent build guide into small, independently readable chunks. The canonical agent instructions remain in [AGENTS.md](AGENTS.md).

## Contents

- [Chunk 01: Mission](#chunk-01-mission)
- [Chunk 02: Agent Operating Rules](#chunk-02-agent-operating-rules)
- [Chunk 03: Product Inputs](#chunk-03-product-inputs)
- [Chunk 04: Product Outputs](#chunk-04-product-outputs)
- [Chunk 05: Required Behavior](#chunk-05-required-behavior)
- [Chunk 06: Target Architecture](#chunk-06-target-architecture)
- [Chunk 07: Technology Choices](#chunk-07-technology-choices)
- [Chunk 08: Model Provider Contract](#chunk-08-model-provider-contract)
- [Chunk 09: Provider Rules](#chunk-09-provider-rules)
- [Chunk 10: Prompt and Claim Safety](#chunk-10-prompt-and-claim-safety)
- [Chunk 11: Processing Pipeline](#chunk-11-processing-pipeline)
- [Chunk 12: Privacy](#chunk-12-privacy)
- [Chunk 13: Security and Reliability](#chunk-13-security-and-reliability)
- [Chunk 14: Frontend Requirements](#chunk-14-frontend-requirements)
- [Chunk 15: Implementation Order](#chunk-15-implementation-order)
- [Chunk 16: Testing](#chunk-16-testing)
- [Chunk 17: Acceptance Gates](#chunk-17-acceptance-gates)
- [Chunk 18: Definition of Done](#chunk-18-definition-of-done)
- [Chunk 19: Product Decisions](#chunk-19-product-decisions)
- [Chunk 20: Conflict Resolution](#chunk-20-conflict-resolution)

---

## Chunk 01: Mission

JIRO is an AI resume tailoring assistant. It accepts a job description and a resume, analyzes job requirements, and produces a keyword-aligned, ATS-friendly resume without fabricating experience.

The essential product flow is:

```text
Resume + Job Description -> ingest -> analyze -> match -> rewrite -> validate -> export
```

The central safety property is non-negotiable: the generated resume may reframe, reorder, or reword facts from the source resume, but it must not invent companies, job titles, dates, skills, responsibilities, achievements, or metrics.

## Chunk 02: Agent Operating Rules

When implementing or changing JIRO:

1. Inspect the existing repository and preserve established conventions before introducing new ones.
2. Prefer the smallest coherent change that advances a roadmap milestone.
3. Keep provider-specific logic behind the model provider interface.
4. Keep parsing, analysis, rewriting, validation, formatting, and export as separate responsibilities.
5. Never log, persist, expose, or send resume or job-description content unnecessarily.
6. Never put API keys in source code, browser-visible build artifacts, logs, tests, fixtures, or committed environment files.
7. Make failure states explicit. A missing key, unsupported file, parser failure, provider timeout, or validation concern must produce an actionable error rather than a fabricated result.
8. Add or update focused tests for every behavior change.
9. Run the narrowest relevant validation after each edit, then run the repository's full checks before finishing.
10. Do not silently change product behavior, provider defaults, privacy guarantees, or the no-fabrication constraint.

If a requirement is ambiguous, choose the implementation that minimizes data exposure and preserves source facts. Record a short decision in the relevant code or documentation only when the decision will affect future work.

## Chunk 03: Product Inputs

The system must accept:

- Resume text or a resume file in PDF, DOCX, or TXT format.
- Job-description text or a job-description file in PDF, DOCX, or TXT format.
- A model configuration selecting the default provider, BYOK provider, or local provider.

Normalize all inputs into a common internal text representation before analysis. Preserve the original input separately so the UI can show the source and the diff view can compare source and output.

## Chunk 04: Product Outputs

The tailoring operation should produce:

- A tailored resume.
- Extracted job requirements, including skills, tools, keywords, and seniority signals.
- Resume-to-job matches and gaps.
- Validation results describing unsupported or suspicious claims.
- A machine-readable diff and a human-readable diff view.
- Exportable Markdown, DOCX, and PDF when those export milestones are implemented.

Do not present a tailored result as trustworthy when validation fails. Preserve warnings with the result so the user can review them.

## Chunk 05: Required Behavior

- Rewrite the summary, relevant experience bullets, and skills ordering using language from the job description where the source resume supports it.
- Do not add unsupported claims merely to improve keyword coverage.
- Make clear which requirements are matched, missing, or uncertain.
- Flag ATS risks such as tables, images, columns, and non-standard fonts when inspecting an uploaded or exported document.
- Show what changed between the original and tailored resume.

## Chunk 06: Target Architecture

Use a frontend/backend split unless the repository already establishes a different architecture:

```text
Frontend (Next.js or Streamlit)
       |
       v
Backend API (FastAPI)
       |
       +--> Input parsers (PDF/DOCX/TXT -> normalized text)
       +--> JD analyzer
       +--> Resume matcher
       +--> Resume rewriter
       +--> Claim validator
       +--> Export renderer
       +--> ModelProvider interface
                  +--> GroqProvider
                  +--> BYOKProvider
                  `--> LocalProvider
```

## Chunk 07: Technology Choices

Suggested technology choices:

- Backend: FastAPI.
- Frontend: Next.js for the full product, or Streamlit for a deliberately scoped MVP.
- PDF parsing: `pdfplumber` or an equivalent maintained parser.
- DOCX parsing and generation: `python-docx`.
- PDF export: a maintained HTML/PDF or DOCX/PDF renderer appropriate to the deployment environment.
- LLM calls: direct provider SDK/API calls first. Add LangChain or LangGraph only when a real multi-step orchestration need justifies the dependency.

Do not introduce both Next.js and Streamlit for the same user experience. Choose one frontend and document the choice in the project README or setup documentation.

## Chunk 08: Model Provider Contract

All model access must pass through one abstraction. The rest of the application must not branch on provider SDKs or provider-specific request formats.

The interface should provide behavior equivalent to:

```text
generate(prompt, config) -> ModelResponse
```

`ModelResponse` should retain enough metadata for diagnostics, such as provider, model, request identifier when available, token usage when available, and finish status. Never include secret values in that metadata.

## Chunk 09: Provider Rules

### Default Groq provider

- Default model: `openai/gpt-oss-120b` through the Groq API.
- Read the server-side fitted/shared key from environment configuration.
- Apply per-user or per-session rate limiting before making calls.
- Return a clear configuration error when the key is absent or invalid.

### BYOK provider

- Support user-supplied keys for supported providers such as Groq, OpenAI, and Anthropic.
- Do not persist BYOK secrets server-side in plaintext.
- Do not include keys in analytics, error messages, request logs, client bundles, URLs, or browser local storage unless the security model explicitly protects them and the user has opted in.
- Enable model selection only after the required provider configuration is valid.

### Local provider

- Support Ollama and OpenAI-compatible local servers.
- Default Ollama endpoint: `http://localhost:11434`.
- Allow a user-configured endpoint, but validate its URL and make network behavior clear.
- Do not route local-provider requests through the shared Groq key.
- Surface connection and model-availability errors without sending resume data to a fallback provider.

## Chunk 10: Prompt and Claim Safety

The no-fabrication rule must be enforced in multiple layers:

1. The system prompt must explicitly prohibit invented facts, metrics, employers, titles, dates, skills, and responsibilities.
2. The rewrite input must identify the source resume as the only authority for candidate facts.
3. The output should use a structured schema or clearly delimited sections so it can be validated.
4. A validator must compare claims in the output against the source resume and report suspicious additions.
5. The UI must make validation warnings visible before export.

Prompts should ask the model to prefer omission over invention. A job-description keyword that is absent from the resume may be reported as a gap; it must not be inserted as candidate experience.

Do not use prompt wording as the only safety mechanism. Treat model output as untrusted input and validate it like any other external data.

## Chunk 11: Processing Pipeline

Implement the pipeline as testable stages with explicit inputs and outputs:

1. **Ingest:** accept text or a supported file, enforce size and type limits, and extract normalized text.
2. **Analyze:** extract job requirements, tools, skills, keywords, and seniority signals.
3. **Match:** compare requirements against resume sections and classify matches, gaps, and uncertain matches.
4. **Rewrite:** tailor only supported sections and preserve source facts.
5. **Validate:** detect new companies, titles, dates, skills, responsibilities, or metrics and produce warnings or a failed validation state.
6. **Format:** create a clean, ATS-compatible document representation.
7. **Export:** render Markdown, DOCX, or PDF without losing content or warnings.

Each stage should be independently testable without requiring a live model call. Use dependency injection or a fake provider in tests.

## Chunk 12: Privacy

Resume and job-description data is sensitive. Apply these rules:

- Minimize retention. Do not add persistent storage until a history feature requires it.
- Do not log raw resume text, job descriptions, prompts, model responses, API keys, or uploaded file contents.
- Sanitize filenames and reject unsafe paths for uploads and exports.
- Enforce upload size, MIME type, and parser limits.
- Treat extracted document text and model output as untrusted content.

## Chunk 13: Security and Reliability

- Configure CORS, request limits, and timeouts deliberately rather than using permissive defaults in production.
- Rate-limit use of the shared Groq key by session, user, or another documented policy.
- Never silently fall back from a local or BYOK provider to the shared provider.
- Make provider timeout, retry, and quota behavior deterministic and bounded.
- Return safe errors to users and keep detailed diagnostics server-side without sensitive payloads.

Target a full rewrite response time below roughly 10 seconds when the selected provider supports it. Correctness, privacy, and validation take priority over latency.

## Chunk 14: Frontend Requirements

The main workflow should make these states obvious:

- Input: resume and job description entered or uploaded.
- Configuration: active provider, model, and privacy mode.
- Analysis: requirements, matches, and gaps.
- Processing: progress and cancellation or timeout state where supported.
- Review: tailored output, warnings, and before/after diff.
- Export: available formats and any blocked exports caused by validation failures.

Do not hide safety warnings behind a secondary page. Do not display secret values after entry. Keep the core text-only MVP usable without file uploads or account creation.

## Chunk 15: Implementation Order

Implement milestones in this order unless repository constraints require a documented change:

1. Establish project structure, configuration loading, and a health check.
2. Build the text-only MVP: pasted resume and JD, single-pass rewrite, plain-text or Markdown output.
3. Add the provider interface with the default Groq provider and a fake provider for tests.
4. Add analysis, matching, structured rewrite output, and claim validation.
5. Add BYOK configuration with secret-handling tests.
6. Add PDF, DOCX, and TXT parsing with file validation.
7. Add local Ollama/OpenAI-compatible provider support.
8. Add diff view and persistent-safe review state.
9. Add DOCX/PDF export and ATS formatting checks.
10. Add multi-resume history/versioning only after retention, deletion, and encryption decisions are explicit.

Do not build history, authentication, or multi-provider breadth ahead of a working and validated text-only flow.

## Chunk 16: Testing

Before considering a milestone complete, verify:

- Unit tests cover parsing, normalization, matching, prompt construction, validation, rate limiting, and export behavior as applicable.
- Provider tests use fakes or mocks and do not require real credentials.
- A fixture containing a missing JD skill proves the system reports a gap instead of inventing the skill.
- A fixture containing unsupported metrics, titles, dates, or companies proves validation catches them.
- Malformed files, oversized files, unsupported types, empty inputs, provider timeouts, and invalid configuration produce useful errors.
- Secrets are absent from logs, serialized responses, test snapshots, and client output.
- The frontend handles loading, success, warning, validation failure, provider failure, and export failure states.
- Full tests, type checks, linting, and build checks pass before delivery.

## Chunk 17: Acceptance Gates

For any model-dependent test, assert the contract and safety behavior rather than a fragile exact wording. Keep deterministic fixtures for all non-model stages.

A milestone is not complete until the tests cover both successful behavior and expected failure states, including missing skills, unsupported claims, malformed files, provider failures, and invalid configuration.

## Chunk 18: Definition of Done

A change is done only when:

1. It satisfies the relevant product contract and does not weaken the no-fabrication rule.
2. It follows the provider, privacy, and module boundaries in this guide.
3. It has focused automated coverage or a clear reason why coverage is not practical.
4. It handles expected failures without leaking sensitive data.
5. It updates setup or API documentation when a developer-facing contract changes.
6. Relevant checks have been run and their result is known.

## Chunk 19: Product Decisions

When implementing these areas, make the choice explicit and keep it reversible:

- **Resume profiles:** multiple base resumes may be useful, but do not add persistence without a retention and deletion policy.
- **Diff granularity:** prefer section-level and line-level changes backed by a structured internal representation.
- **Shared-key rate limiting:** begin with a bounded per-session policy for the MVP; make the policy configurable and document production storage requirements.
- **Frontend choice:** use Next.js for the intended product experience; use Streamlit only when intentionally optimizing for a fast prototype.
- **Export engine:** choose based on deployment support, font consistency, ATS output quality, and testability rather than convenience alone.

## Chunk 20: Conflict Resolution

When a future agent encounters a conflict between this guide and existing code, preserve user data, provider isolation, and no-fabrication behavior first. Then update the smallest affected surface and add a regression test.
