"""Stable dependency boundaries for the JIRO processing architecture."""

from typing import Protocol

from app.ingest import IngestedDocument
from app.outputs import (
    ExportResult,
    Requirement,
    TailoringResult,
    ValidationResult,
)
from app.model_provider import ModelConfig, ModelProvider, ModelProviderError, ModelResponse


class InputParser(Protocol):
    """Convert pasted or uploaded input into normalized documents."""

    def parse_text(self, text: str, *, source_name: str) -> IngestedDocument:
        ...

    def parse_file(
        self,
        filename: str,
        content: bytes,
        *,
        content_type: str | None = None,
    ) -> IngestedDocument:
        ...


class JobAnalyzer(Protocol):
    """Extract structured requirements from a job description."""

    def analyze(self, job_description: str) -> tuple[Requirement, ...]:
        ...


class ResumeMatcher(Protocol):
    """Classify job requirements against source resume evidence."""

    def match(
        self,
        resume: str,
        requirements: tuple[Requirement, ...],
    ) -> tuple[tuple[Requirement, ...], tuple[Requirement, ...]]:
        ...


class ResumeRewriter(Protocol):
    """Rewrite only source-supported resume content."""

    def rewrite(self, resume: str, job_description: str) -> str:
        ...


class ClaimValidator(Protocol):
    """Check generated content for unsupported claims and ATS risks."""

    def validate(self, original_resume: str, tailored_resume: str) -> ValidationResult:
        ...


class ResumeFormatter(Protocol):
    """Create the ATS-compatible internal document before export rendering."""

    def format(self, resume: str) -> str:
        ...


class ExportRenderer(Protocol):
    """Render validated output into an explicitly named export format."""

    def export(self, resume: str) -> tuple[ExportResult, ...]:
        ...


class TailoringPipeline(Protocol):
    """Orchestrate stages without exposing provider-specific details to the API."""

    def run(self, resume: str, job_description: str) -> TailoringResult:
        ...
