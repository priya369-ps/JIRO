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