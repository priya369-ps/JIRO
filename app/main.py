"""Minimal JIRO service foundation for the mission milestone."""

from fastapi import FastAPI


PRODUCT_NAME = "JIRO"
MISSION = "Tailor resumes to job descriptions without fabricating candidate experience."
PIPELINE_STAGES = (
    "ingest",
    "analyze",
    "match",
    "rewrite",
    "validate",
    "export",
)

app = FastAPI(title=PRODUCT_NAME, version="0.1.0")


@app.get("/health")
def health_check() -> dict[str, object]:
    """Return service status and the product contract's initial pipeline."""
    return {
        "status": "ok",
        "service": PRODUCT_NAME,
        "mission": MISSION,
        "pipeline": list(PIPELINE_STAGES),
        "fabrication_policy": "never_invent_source_facts",
    }
