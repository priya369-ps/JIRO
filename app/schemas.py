"""Typed API schemas shared by the backend contract and documentation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TailoringRequest(APIModel):
    resume: str
    job_description: str
    provider: Literal["groq", "byok", "local"] = "groq"
    model: str | None = None
    privacy_mode: Literal["ephemeral"] = "ephemeral"


class RewriteOutput(APIModel):
    summary: str
    experience: list[str]
    skills: list[str]
    unsupported_claims: list[str]


class WorkflowMetadata(APIModel):
    state: Literal["input", "processing", "review", "export"]
    privacy_mode: Literal["ephemeral"]
    validation_status: str | None = None
    warnings_present: bool = False
    export_blocked: bool = False
    available_exports: list[str] = Field(default_factory=list)


class SafeError(APIModel):
    detail: str
    category: Literal["input", "configuration", "provider", "validation", "export", "unknown"] = "unknown"
