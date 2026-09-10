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


## Chunk 21: Frontend Project

Create the planned Next.js frontend as a separate application surface. Keep it
separate from the FastAPI backend and do not introduce Streamlit alongside it.

Implement:

- A frontend package and local development command.
- Environment-based backend URL configuration.
- Typed API client functions for health, text ingestion, file ingestion, and
       tailoring.
- A predictable loading, success, and error state model.
- A frontend test command and production build command.

The frontend must run without a model key because the backend owns provider
configuration. Do not place API keys or resume content in the client bundle.

Completion requires the frontend to start locally, reach the FastAPI health
endpoint, and fail safely when the backend is unavailable.

## Chunk 22: Input Experience

Build the primary input screen for the resume and job description workflow.

Implement:

- Resume text input and resume file upload.
- Job-description text input and job-description file upload.
- Accepted file type and size messages.
- Clear empty-input and parser-error states.
- A visible ephemeral privacy mode indicator.
- A submit action disabled until both required inputs are valid.

The UI must not echo secrets, store raw documents in persistent browser storage,
or silently replace pasted content with uploaded content. Upload and paste
paths must produce equivalent normalized backend inputs.

## Chunk 23: Provider Configuration UI

Add provider configuration controls that map to the provider-neutral backend
contract.

Implement:

- Default Groq mode with model status but no exposed shared key.
- BYOK mode with provider and model fields.
- Local mode with endpoint and model fields.
- Secret inputs that are never displayed after entry.
- Validation before model selection is enabled.
- Explicit privacy and network behavior for each mode.

BYOK values must not be written to local storage, URLs, analytics, or logs.
Local mode must never silently fall back to Groq or another remote provider.

## Chunk 24: API Workflow Contract

Stabilize the frontend/backend API contract before adding live model rewriting.

Define typed request and response schemas for:

- Input documents and source metadata.
- Provider configuration without serializing secrets.
- Job requirements, matches, gaps, and uncertain matches.
- Tailored resume output.
- Validation warnings and export blocking.
- Machine-readable and human-readable diffs.
- Workflow state and safe error responses.

Add contract tests that exercise the schemas through the API. Backward-incompatible
changes require a documented versioning decision and updated frontend types.

## Chunk 25: Live Rewrite Orchestration

Replace the source-preserving rewrite stage with an injected model-backed rewrite
stage while retaining the deterministic implementation as the test default.

Implement:

- Prompt construction through the Chunk 10 safety module.
- Provider selection through `ModelProvider` only.
- Structured model output parsing.
- Bounded provider timeout and retry behavior.
- Cancellation or request-abort handling where supported.
- Safe provider errors with no raw prompt or response content in diagnostics.

The rewrite stage may change only supported summary, experience, and skills
content. It must prefer omission over invention and must send the result through
claim validation before it can be exported.

## Chunk 26: Structured Model Output

Require model responses to conform to the structured rewrite schema.

Implement:

- JSON parsing with strict type validation.
- Required `summary`, `experience`, `skills`, and `unsupported_claims` fields.
- Rejection of malformed or extra unsafe output where appropriate.
- A deterministic fallback to a reviewable failure state, never a fabricated
       resume.
- Tests for valid JSON, malformed JSON, missing fields, wrong field types, and
       prompt-injection text inside model output.

Treat the model response as untrusted external input. Do not execute, render as
HTML, or interpret model-provided markup as code.

## Chunk 27: Requirement Analysis

Improve deterministic and model-assisted job-description analysis.

Extract and classify:

- Required and preferred skills.
- Tools, platforms, languages, and frameworks.
- Seniority and experience signals.
- Responsibilities and domain keywords.
- Explicit years, certifications, education, and location requirements.

Preserve the source phrase for every extracted requirement. Add confidence and
evidence fields where the classification is uncertain. A requirement absent
from the resume must remain a gap rather than becoming a candidate claim.

## Chunk 28: Matching and Evidence

Improve resume-to-job matching beyond raw substring checks.

Implement:

- Case-insensitive normalized matching.
- Alias handling only for verified, documented equivalents.
- Evidence references to resume sections or lines.
- Match, gap, and uncertain classifications.
- Separate candidate evidence from job-description language.
- Tests for synonyms, false positives, negated skills, and missing skills.

Do not mark a requirement as matched solely because it appears in the job
description or in an unsupported model-generated phrase.

## Chunk 29: Review and Diff Experience

Build the review screen around user verification rather than automatic trust.

Display:

- Original and tailored resume side by side or in a clear before/after view.
- Section-level and line-level changes.
- Added, removed, and rewritten text.
- Requirement matches, gaps, and uncertain items.
- Validation warnings before any export action.
- A clear failed-validation state.

Do not hide safety warnings behind a secondary settings page. The UI must not
present a failed validation result as ready to send.

## Chunk 30: Export Foundation

Implement a common export representation and renderer interface.

Implement:

- A normalized resume document model.
- Stable section ordering.
- Plain-text and Markdown rendering.
- Consistent escaping for user and model text.
- Export metadata that preserves validation warnings.
- Export blocking when validation fails.

Export functions must be deterministic for the same validated input and must
never write files outside an explicitly controlled destination.

## Chunk 31: DOCX Export

Implement DOCX export using the selected maintained renderer and the existing
document representation.

Requirements:

- ATS-readable single-column layout by default.
- Standard fonts and headings.
- No hidden text, images, tables, or decorative columns in the default output.
- Stable section and bullet formatting.
- Safe filename generation.
- Tests that reopen the generated DOCX and verify content preservation.

DOCX export remains blocked when claim validation fails or rendering loses
content. Record renderer errors without logging resume content.

## Chunk 32: PDF Export

Implement PDF export using a maintained renderer appropriate to the deployment
environment.

Requirements:

- Reuse the same validated document representation as DOCX and Markdown.
- Preserve section order and text content.
- Use embedded or deployment-safe standard fonts.
- Avoid layouts that produce unreadable ATS text extraction.
- Provide actionable renderer errors.
- Add text-extraction tests against generated PDFs.

Do not introduce a PDF-only formatting path that can diverge from validation or
the other export formats.

## Chunk 33: ATS Inspection

Expand ATS checks for uploaded and generated documents.

Detect and report:

- Tables, columns, text boxes, images, and decorative shapes.
- Non-standard or missing fonts.
- Headers and footers that may be ignored.
- Unreadable text order.
- Unsupported symbols and excessive formatting.
- Missing contact information or section headings where applicable.

Return structured risks with severity and evidence. ATS risks are warnings by
default, while claim-safety failures remain export-blocking unless a deliberate
product decision says otherwise.

## Chunk 34: Error and Recovery UX

Make all expected failures actionable in the frontend and API.

Handle:

- Empty or malformed inputs.
- Unsupported files and size limits.
- Missing provider configuration.
- Invalid BYOK configuration.
- Local endpoint unavailable.
- Provider timeout, quota, and malformed response.
- Rewrite validation failure.
- Export renderer failure.

Each error must identify the safe next action without exposing credentials,
resume text, prompts, provider payloads, or stack traces to the user.

## Chunk 35: Observability Without Sensitive Data

Add operational diagnostics that do not capture sensitive content.

Record only safe metadata such as:

- Request correlation ID.
- Route and stage name.
- Provider name and model name.
- Duration and bounded token counts.
- Safe error category.
- Validation status and export format.

Never log resumes, job descriptions, prompts, model responses, uploaded files,
API keys, authorization headers, or raw exception payloads. Add tests that scan
captured logs for sensitive fixtures and secrets.

## Chunk 36: Rate Limiting and Quotas

Replace the in-memory shared-provider limiter with a deployment-appropriate
bounded store when the application is deployed across processes or instances.

Implement:

- Per-session or authenticated-user limits.
- Separate limits for shared Groq and user-owned providers.
- Deterministic retry-after behavior.
- Provider quota error mapping.
- No fallback across privacy boundaries.
- Tests for concurrent and window-expiration behavior.

Document the chosen production store and its retention behavior. Do not persist
resume or job-description content in the rate-limit store.

## Chunk 37: Authentication and Account Boundaries

Add authentication only after the text-only anonymous workflow is complete and
privacy requirements are explicit.

If authentication is introduced:

- Keep provider secrets separate from account data.
- Do not persist resumes by default.
- Require explicit opt-in for saved profiles or history.
- Provide deletion and retention controls.
- Scope rate limits and saved data to the authenticated user.
- Add authorization tests for every persisted resource.

Authentication must not become a prerequisite for the core ephemeral workflow
unless a documented product decision changes that requirement.

## Chunk 38: Resume History and Versioning

Implement history only after storage, deletion, and encryption decisions are
approved.

Store only what is necessary for the selected feature, with:

- Explicit user consent.
- Retention and deletion policy.
- Version identifiers.
- Original and tailored relationship tracking.
- Validation and warning preservation.
- Access control and encrypted storage where required.

History must never silently activate for users who selected ephemeral mode.

## Chunk 39: Production Deployment

Prepare the backend and frontend for deployment without weakening privacy.

Implement and document:

- Separate development and production configuration.
- Secret injection through the deployment platform.
- HTTPS and secure cookie policy if authentication exists.
- Restrictive CORS origins.
- Request and upload limits.
- Health and readiness endpoints.
- Graceful shutdown and bounded worker behavior.
- Dependency and container scanning.

Do not commit production credentials, generated uploads, local databases, or
deployment-specific secrets.

## Chunk 40: End-to-End Verification

Add end-to-end tests for the complete user workflow:

1. Enter or upload a resume.
2. Enter or upload a job description.
3. Select a provider configuration.
4. Analyze requirements and matches.
5. Run a fake-provider rewrite.
6. Display the before/after review and warnings.
7. Block export for unsupported claims.
8. Export a validated document.

Run the same scenarios for successful output, missing skills, malformed input,
provider failure, timeout, invalid configuration, and validation failure. E2E
tests must use deterministic fixtures and fake providers unless an explicit
staging integration test is being run.

## Chunk 41: Performance Verification

Measure the full rewrite path under representative resume and job-description
sizes.

Track:

- Input parsing duration.
- Analysis and matching duration.
- Provider request duration.
- Validation duration.
- Export duration.
- Total response time.
- Memory use during upload and parsing.

Keep the normal supported-provider path near the ten-second target when the
provider permits it. Enforce bounded timeouts and reject inputs that could cause
unbounded memory or processing growth.

## Chunk 42: Accessibility and Usability

Audit the Next.js workflow for keyboard, screen-reader, and responsive use.

Verify:

- Every input has a label and useful error association.
- Loading and failure states are announced.
- Warnings are not conveyed by color alone.
- Diff additions and removals have accessible text labels.
- Export blocking is visible and understandable.
- The workflow works on mobile and desktop widths.

Accessibility changes must not hide privacy or validation information.

## Chunk 43: Documentation and Operations

Keep developer and operator documentation synchronized with the implementation.

Document:

- Local setup and test commands.
- Environment variables and safe example values.
- Provider configuration behavior.
- Privacy and retention behavior.
- API request and response schemas.
- Deployment requirements.
- Troubleshooting for parser, provider, validation, and export failures.
- The supported and intentionally deferred feature set.

Never include real API keys, user documents, or sensitive fixtures in examples.

## Chunk 44: Final Release Gate

Before calling the full project complete, verify all of the following:

- Backend tests, frontend tests, type checks, linting, and builds pass.
- Acceptance gates pass without live credentials.
- End-to-end workflows pass with fake providers.
- Provider integrations have isolated integration tests where required.
- No-fabrication validation blocks unsupported claims.
- Privacy scans find no secrets or sensitive fixture content in logs or builds.
- DOCX, PDF, and Markdown exports preserve validated content.
- ATS warnings and validation failures are visible before export.
- Ephemeral mode does not persist documents.
- Authentication and history, if present, enforce retention and deletion rules.
- Deployment configuration uses injected secrets and restrictive network policy.
- Documentation reflects the actual implemented feature set.

The final release report must list completed chunks, deferred decisions, test
commands and results, known limitations, and any required production setup.
