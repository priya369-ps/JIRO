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