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
    requirements = _extract_requirements(job_description)
    resume_lower = resume.casefold()
    matches = tuple(
        requirement
        for requirement in requirements
        if requirement.value.casefold() in resume_lower
    )
    matched_values = {requirement.value for requirement in matches}
    gaps = tuple(
        requirement
        for requirement in requirements
        if requirement.value not in matched_values
    )
    matches = tuple(
        Requirement(item.value, item.category, "matched", f"Found in source resume: {item.value}")
        for item in matches
    )
    gaps = tuple(
        Requirement(item.value, item.category, "gap", None)
        for item in gaps
    )

    tailored_resume = resume.strip()
    ats_risks = _detect_ats_risks(resume)
    warnings = [
        "No model rewrite was applied; the tailored resume preserves the source resume exactly."
    ]
    warnings.extend(f"ATS risk: {risk}." for risk in ats_risks)
    validation = ValidationResult(
        status="passed",
        warnings=tuple(warnings),
        export_blocked=False,
        ats_risks=ats_risks,
    )
    diff = _build_diff(resume, tailored_resume)
    exports = (
        ExportResult("markdown", True, _markdown_export(tailored_resume), None),
        ExportResult("docx", False, None, "DOCX export is planned for a later milestone."),
        ExportResult("pdf", False, None, "PDF export is planned for a later milestone."),
    )
    return TailoringResult(
        tailored_resume=tailored_resume,
        job_requirements=requirements,
        matches=matches,
        gaps=gaps,
        validation=validation,
        diff=diff,
        exports=exports,
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
