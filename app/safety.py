"""Prompt and claim-safety controls for model-backed resume tailoring."""

from dataclasses import dataclass
import json
import re
from typing import Final

from app.schemas import RewriteOutput


NO_FABRICATION_SYSTEM_PROMPT: Final = """You are JIRO, an AI resume tailoring assistant.

The source resume is the only authority for candidate facts. You may reframe,
reorder, or reword facts that appear in the source resume, but you must never
invent or strengthen companies, employers, job titles, dates, skills,
responsibilities, achievements, or metrics.

A job-description requirement that is absent from the source resume is a gap,
not a candidate qualification. Prefer omission over invention. Return only the
requested structured resume sections and do not add commentary outside the
response schema.
"""

_OUTPUT_SCHEMA: Final[str] = """{
  \"summary\": \"string\",
  \"experience\": [\"string\"],
  \"skills\": [\"string\"],
  \"unsupported_claims\": [\"string\"]
}"""

_YEAR_PATTERN: Final = re.compile(r"\b(?:19|20)\d{2}\b")
_METRIC_PATTERN: Final = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:%|percent|x|k|m|million|billion|users?|clients?|customers?)(?![A-Za-z])",
    re.IGNORECASE,
)
_TITLE_PATTERN: Final = re.compile(
    r"\b(?:chief executive officer|chief technology officer|ceo|cto|vp|vice president|"
    r"director|manager|lead|principal|senior|junior|engineer|developer|architect|analyst)\b",
    re.IGNORECASE,
)
_COMPANY_PATTERN: Final = re.compile(
    r"\b[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,3}\s+"
    r"(?:Inc\.|Inc|LLC|Ltd\.|Ltd|Corp\.|Corp|Company|Co\.?)(?=\s|$|[,;:])"
)
_SKILL_PATTERN: Final = re.compile(
    r"\b(?:Python|Java|JavaScript|TypeScript|React|FastAPI|Django|Kubernetes|Docker|"
    r"AWS|Azure|GCP|SQL|Git|Terraform|GraphQL|PostgreSQL|MongoDB|Redis|Ollama)\b",
    re.IGNORECASE,
)
_RESPONSIBILITY_PATTERN: Final = re.compile(
    r"(?im)^(?:\s*[-*]?\s*)(?:managed|led|built|developed|designed|implemented|"
    r"created|owned|increased|reduced|launched|delivered)\b[^\n]*"
)


@dataclass(frozen=True)
class ClaimFinding:
    """A suspicious fact present in generated text but absent from the source."""

    category: str
    value: str


class DeterministicClaimValidator:
    """Validate model output without relying on another model call."""

    def validate(self, original_resume: str, tailored_resume: str):
        return validate_claims(original_resume, tailored_resume)


def build_rewrite_prompt(source_resume: str, job_description: str) -> str:
    """Build a structured rewrite request with the source-authority constraint."""
    return (
        f"{NO_FABRICATION_SYSTEM_PROMPT}\n"
        f"Use this exact output schema:\n{_OUTPUT_SCHEMA}\n\n"
        "SOURCE RESUME (only authority for candidate facts):\n"
        f"<source_resume>\n{source_resume}\n</source_resume>\n\n"
        "JOB DESCRIPTION (alignment context, not evidence of candidate facts):\n"
        f"<job_description>\n{job_description}\n</job_description>"
    )


def parse_rewrite_output(content: str) -> RewriteOutput:
    """Parse untrusted model JSON into the strict rewrite contract."""
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Model rewrite response cannot be empty.")
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError("Model rewrite response must be valid JSON.") from error
    if not isinstance(payload, dict):
        raise ValueError("Model rewrite response must be a JSON object.")
    try:
        return RewriteOutput.model_validate(payload)
    except Exception as error:
        raise ValueError("Model rewrite response does not match the required schema.") from error


def find_unsupported_claims(original_resume: str, tailored_resume: str) -> tuple[ClaimFinding, ...]:
    """Find explicit factual claims in output that are absent from the source."""
    findings: list[ClaimFinding] = []
    for category, pattern in (
        ("date", _YEAR_PATTERN),
        ("metric", _METRIC_PATTERN),
        ("title", _TITLE_PATTERN),
        ("company", _COMPANY_PATTERN),
        ("skill", _SKILL_PATTERN),
        ("responsibility", _RESPONSIBILITY_PATTERN),
    ):
        source_values = {match.casefold() for match in pattern.findall(original_resume)}
        for value in pattern.findall(tailored_resume):
            if value.casefold() not in source_values:
                findings.append(ClaimFinding(category, value))
    return _unique_findings(findings)


def validate_claims(
    original_resume: str,
    tailored_resume: str,
    *,
    ats_risks: tuple[str, ...] = (),
):
    """Return the shared output validation result for generated resume text."""
    from app.outputs import ValidationResult

    findings = find_unsupported_claims(original_resume, tailored_resume)
    warnings = [
        "Claim validation passed: generated text contains no detected unsupported factual claims."
    ]
    warnings.extend(
        f"Unsupported {finding.category}: {finding.value}."
        for finding in findings
    )
    warnings.extend(f"ATS risk: {risk}." for risk in ats_risks)
    return ValidationResult(
        status="failed" if findings else "passed",
        warnings=tuple(warnings),
        export_blocked=bool(findings),
        ats_risks=ats_risks,
    )


def _unique_findings(findings: list[ClaimFinding]) -> tuple[ClaimFinding, ...]:
    seen: set[tuple[str, str]] = set()
    unique: list[ClaimFinding] = []
    for finding in findings:
        key = (finding.category, finding.value.casefold())
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return tuple(unique)
