"""Concrete, independently testable processing stages for JIRO."""

from app.architecture import (
    ClaimValidator,
    ExportRenderer,
    JobAnalyzer,
    ResumeMatcher,
    ResumeRewriter,
    ResumeFormatter,
    TailoringPipeline,
)
from app.ingest import IngestedDocument, ingest_file, ingest_text
from app.outputs import (
    TailoringResult,
    build_diff,
    detect_ats_risks,
    extract_requirements,
    match_requirements,
)
from app.safety import validate_claims


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


class DefaultJobAnalyzer:
    """Analyze job-description text into deterministic requirements."""

    def analyze(self, job_description: str):
        return extract_requirements(job_description)


class DefaultResumeMatcher:
    """Match requirements against source resume evidence."""

    def match(self, resume: str, requirements):
        return match_requirements(resume, requirements)


class SourcePreservingRewriter:
    """Deterministic rewrite stage that cannot invent candidate facts."""

    def rewrite(self, resume: str, job_description: str) -> str:
        return resume.strip()


class DefaultClaimValidator:
    """Validate rewritten text and attach ATS risks before export."""

    def validate(self, original_resume: str, tailored_resume: str):
        return validate_claims(
            original_resume,
            tailored_resume,
            ats_risks=detect_ats_risks(original_resume),
        )


class DefaultResumeFormatter:
    """Preserve the current text representation until format exporters exist."""

    def format(self, resume: str) -> str:
        return resume


class DefaultExportRenderer:
    """Render only formats supported by the current milestone."""

    def export(self, resume: str):
        from app.outputs import render_exports

        return render_exports(resume)


class DeterministicTailoringPipeline:
    """Orchestrate ingest-adjacent processing stages with injectable dependencies."""

    def __init__(
        self,
        *,
        analyzer: JobAnalyzer | None = None,
        matcher: ResumeMatcher | None = None,
        rewriter: ResumeRewriter | None = None,
        validator: ClaimValidator | None = None,
        formatter: ResumeFormatter | None = None,
        exporter: ExportRenderer | None = None,
    ) -> None:
        self.analyzer = analyzer or DefaultJobAnalyzer()
        self.matcher = matcher or DefaultResumeMatcher()
        self.rewriter = rewriter or SourcePreservingRewriter()
        self.validator = validator or DefaultClaimValidator()
        self.formatter = formatter or DefaultResumeFormatter()
        self.exporter = exporter or DefaultExportRenderer()

    def run(self, resume: str, job_description: str) -> TailoringResult:
        requirements = self.analyzer.analyze(job_description)
        matches, gaps = self.matcher.match(resume, requirements)
        tailored_resume = self.rewriter.rewrite(resume, job_description)
        formatted_resume = self.formatter.format(tailored_resume)
        validation = self.validator.validate(resume, formatted_resume)
        return TailoringResult(
            tailored_resume=formatted_resume,
            job_requirements=requirements,
            matches=matches,
            gaps=gaps,
            validation=validation,
            diff=build_diff(resume, formatted_resume),
            exports=self.exporter.export(formatted_resume)
            if not validation.export_blocked
            else tuple(),
        )


def build_default_pipeline() -> TailoringPipeline:
    """Return the application pipeline selected for the current milestone."""
    return DeterministicTailoringPipeline()
