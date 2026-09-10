"""Structured tailoring outputs for the deterministic MVP boundary."""

from dataclasses import asdict, dataclass
from difflib import unified_diff
import re
from typing import Final


_TOKEN_PATTERN: Final = re.compile(r"[A-Za-z][A-Za-z0-9+#./-]{1,}")
_STOP_WORDS: Final = frozenset(
    {
        "about",
        "after",
        "and",
        "are",
        "for",
        "from",
        "have",
        "into",
        "that",
        "the",
        "their",
        "this",
        "with",
        "you",
    }
)


@dataclass(frozen=True)
class Requirement:
    """A job-description requirement and its source-backed match status."""

    value: str
    category: str
    status: str
    evidence: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Safety result attached to every tailoring output."""

    status: str
    warnings: tuple[str, ...]
    export_blocked: bool
    ats_risks: tuple[str, ...] = ()


@dataclass(frozen=True)
class DiffResult:
    """Machine-readable and human-readable source/output comparison."""

    changed: bool
    unified: str
    summary: str


@dataclass(frozen=True)
class ExportResult:
    """Export availability and content for a tailoring result."""

    format: str
    available: bool
    content: str | None
    reason: str | None = None


@dataclass(frozen=True)
class TailoringResult:
    """Complete output contract for the tailoring operation."""

    tailored_resume: str
    job_requirements: tuple[Requirement, ...]
    matches: tuple[Requirement, ...]
    gaps: tuple[Requirement, ...]
    validation: ValidationResult
    diff: DiffResult
    exports: tuple[ExportResult, ...]

    def as_dict(self) -> dict[str, object]:
        """Serialize the immutable domain result for the API response."""
        return asdict(self)


def _detect_ats_risks(resume: str) -> tuple[str, ...]:
    """Detect document structures that are unsafe for plain-text ATS parsing."""
    risks: list[str] = []
    lines = resume.splitlines()
    if any("\t" in line for line in lines):
        risks.append("tab-separated columns may be difficult for ATS parsers to read")
    if any(line.count("|") >= 2 for line in lines):
        risks.append("table-like content may be difficult for ATS parsers to read")
    if re.search(r"!\[[^\]]*\]\([^)]*\)|\[(?:image|photo|logo)\]", resume, re.IGNORECASE):
        risks.append("images may be ignored by ATS parsers")
    return tuple(risks)


def build_tailoring_result(resume: str, job_description: str) -> TailoringResult:
    """Build a safe source-preserving result without inventing candidate facts."""
    requirements = extract_requirements(job_description)
    matches, gaps = match_requirements(resume, requirements)

    tailored_resume = resume.strip()
    ats_risks = detect_ats_risks(resume)
    from app.safety import validate_claims

    validation = validate_claims(resume, tailored_resume, ats_risks=ats_risks)
    diff = build_diff(resume, tailored_resume)
    exports = render_exports(tailored_resume)
    return TailoringResult(
        tailored_resume=tailored_resume,
        job_requirements=requirements,
        matches=matches,
        gaps=gaps,
        validation=validation,
        diff=diff,
        exports=exports,
    )


def extract_requirements(job_description: str) -> tuple[Requirement, ...]:
    """Analyze a job description into deterministic, deduplicated requirements."""
    return _extract_requirements(job_description)


def match_requirements(
    resume: str,
    requirements: tuple[Requirement, ...],
) -> tuple[tuple[Requirement, ...], tuple[Requirement, ...]]:
    """Match requirements against resume text without changing either input."""
    resume_lower = resume.casefold()
    matches = tuple(
        Requirement(item.value, item.category, "matched", f"Found in source resume: {item.value}")
        for item in requirements
        if item.value.casefold() in resume_lower
    )
    matched_values = {requirement.value.casefold() for requirement in matches}
    gaps = tuple(
        Requirement(item.value, item.category, "gap", None)
        for item in requirements
        if item.value.casefold() not in matched_values
    )
    return matches, gaps


def detect_ats_risks(resume: str) -> tuple[str, ...]:
    """Analyze resume text for structures that can reduce ATS readability."""
    return _detect_ats_risks(resume)


def build_diff(original: str, tailored: str) -> DiffResult:
    """Create the machine-readable and human-readable comparison result."""
    return _build_diff(original, tailored)


def render_exports(resume: str) -> tuple[ExportResult, ...]:
    """Render supported output formats and report deferred formats explicitly."""
    return (
        ExportResult("markdown", True, _markdown_export(resume), None),
        ExportResult("docx", False, None, "DOCX export is planned for a later milestone."),
        ExportResult("pdf", False, None, "PDF export is planned for a later milestone."),
    )


def _extract_requirements(job_description: str) -> tuple[Requirement, ...]:
    seen: set[str] = set()
    requirements: list[Requirement] = []
    for token in _TOKEN_PATTERN.findall(job_description):
        normalized = token.strip(".,:;()[]{}")
        key = normalized.casefold()
        if len(normalized) < 3 or key in _STOP_WORDS or key in seen:
            continue
        seen.add(key)
        category = "tool_or_skill" if any(character in normalized for character in "+#./-") else "keyword"
        requirements.append(Requirement(normalized, category, "unmatched", None))
    return tuple(requirements)


def _build_diff(original: str, tailored: str) -> DiffResult:
    lines = tuple(
        unified_diff(
            original.splitlines(),
            tailored.splitlines(),
            fromfile="original_resume",
            tofile="tailored_resume",
            lineterm="",
        )
    )
    changed = original != tailored
    if changed:
        summary = "The tailored resume differs from the original source."
    else:
        summary = "No source text was changed."
    return DiffResult(changed, "\n".join(lines), summary)


def _markdown_export(resume: str) -> str:
    return f"# Tailored Resume\n\n{resume}\n"
