"""JIRO API and input ingestion endpoints."""

from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse

from app.config import load_settings
from app.decisions import ProductDecisions
from app.auth import AuthenticationMiddleware
from app.errors import public_error
from app.ingest import IngestionError
from app.model_provider import ModelProviderError, ProviderRateLimitError
from app.exporters import ExportError
from app.pipeline import DefaultInputParser, build_default_pipeline
from app.reliability import RequestSizeLimitMiddleware, cors_origins
from app.telemetry import CorrelationIdMiddleware
from app.schemas import TailoringRequest
from app.workflow import input_workflow_state, review_workflow_state


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
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
settings = load_settings()
input_parser = DefaultInputParser()
tailoring_pipeline = build_default_pipeline()


@app.exception_handler(ModelProviderError)
async def provider_error_handler(request: Request, error: ModelProviderError) -> JSONResponse:
    if isinstance(error, ProviderRateLimitError):
        return JSONResponse(
            status_code=429,
            content={"detail": str(error), "category": "provider"},
            headers={"Retry-After": str(error.retry_after)},
        )
    category = "configuration" if "configured" in str(error).lower() else "provider"
    public = public_error(category, str(error))
    return JSONResponse(status_code=public.status_code, content=public.payload.model_dump())


@app.exception_handler(ExportError)
async def export_error_handler(request: Request, error: ExportError) -> JSONResponse:
    public = public_error("export", str(error))
    return JSONResponse(status_code=public.status_code, content=public.payload.model_dump())


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
    public = public_error("unknown", "The request could not be completed safely.")
    return JSONResponse(status_code=public.status_code, content=public.payload.model_dump())


class TextInput(BaseModel):
    """Pasted resume or job-description input."""

    text: str
    source_name: str = "pasted-text"
    provider: Literal["groq", "byok", "local"] = "groq"
    model: str | None = None
    privacy_mode: Literal["ephemeral"] = "ephemeral"


class TailoringInput(TailoringRequest):
    """Source inputs for the structured tailoring output contract."""


@app.get("/health")
def health_check() -> dict[str, object]:
    """Return service status and the product contract's initial pipeline."""
    return {
        "status": "ok",
        "service": PRODUCT_NAME,
        "mission": MISSION,
        "pipeline": list(PIPELINE_STAGES),
        "fabrication_policy": "never_invent_source_facts",
        "configuration": settings.public_metadata(),
    }


@app.get("/ready")
def readiness_check() -> dict[str, object]:
    """Report readiness without contacting external model providers."""
    return {
        "status": "ready",
        "service": PRODUCT_NAME,
        "checks": {"configuration": "loaded", "provider": "deferred_until_request"},
        "configuration": {"product_decisions": ProductDecisions().as_dict()},
    }


@app.post("/ingest/text")
def ingest_text_input(input_data: TextInput) -> dict[str, object]:
    try:
        document = input_parser.parse_text(
            input_data.text,
            source_name=input_data.source_name,
        )
    except IngestionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "source_name": document.source_name,
        "source_type": document.source_type,
        "original_text": document.original_text,
        "normalized_text": document.normalized_text,
        "provider": input_data.provider,
        "model": input_data.model or "",
        "workflow": input_workflow_state(),
    }


@app.post("/ingest/file")
async def ingest_file_input(
    file: UploadFile = File(...),
    provider: Literal["groq", "byok", "local"] = Form("groq"),
    model: str | None = Form(None),
) -> dict[str, object]:
    try:
        document = input_parser.parse_file(
            file.filename or "",
            await file.read(5 * 1024 * 1024 + 1),
            content_type=file.content_type,
        )
    except IngestionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "source_name": document.source_name,
        "source_type": document.source_type,
        "original_text": document.original_text,
        "normalized_text": document.normalized_text,
        "provider": provider,
        "model": model or "",
        "workflow": input_workflow_state(),
    }


@app.post("/tailor")
def tailor_resume(input_data: TailoringInput) -> dict[str, object]:
    """Return all Chunk 4 outputs while preserving the source resume."""
    try:
        resume = input_parser.parse_text(
            input_data.resume,
            source_name="resume",
        ).normalized_text
        job_description = input_parser.parse_text(
            input_data.job_description,
            source_name="job-description",
        ).normalized_text
    except IngestionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    result = tailoring_pipeline.run(resume, job_description)
    response = result.as_dict()
    response["workflow"] = review_workflow_state(result)
    response["provider"] = input_data.provider
    response["model"] = input_data.model or ""
    return response
