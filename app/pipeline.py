"""Concrete dependency wiring for the current deterministic JIRO pipeline."""

from app.architecture import TailoringPipeline
from app.ingest import IngestedDocument, ingest_file, ingest_text
from app.outputs import TailoringResult, build_tailoring_result


class DefaultInputParser:
    """Adapter exposing the ingestion module through the architecture contract."""

    def parse_text(self, text: str, *, source_name: str) -> IngestedDocument:
        return ingest_text(text, source_name=source_name)

    def parse_file(
        self,
        filename: str,
        content: bytes,
        *,
        content_type: str | None = None,
    ) -> IngestedDocument:
        return ingest_file(filename, content, content_type=content_type)


class DeterministicTailoringPipeline:
    """Current pipeline implementation with provider-independent composition."""

    def run(self, resume: str, job_description: str) -> TailoringResult:
        return build_tailoring_result(resume, job_description)


def build_default_pipeline() -> TailoringPipeline:
    """Return the application pipeline selected for the current milestone."""
    return DeterministicTailoringPipeline()
