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
_ALIASES: Final = {
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "js": "javascript",
    "ts": "typescript",
}
_SKILL_TERMS: Final = frozenset(
    {"python", "javascript", "typescript", "react", "fastapi", "docker", "kubernetes", "postgresql", "sql"}
)


@dataclass(frozen=True)
class Requirement:
    """A job-description requirement and its source-backed match status."""

    value: str
    category: str
    status: str
    evidence: str | None = None
    confidence: float = 1.0


@dataclass(frozen=True)
class ValidationResult:
    """Safety result attached to every tailoring output."""

    status: str
    warnings: tuple[str, ...]
    export_blocked: bool
    ats_risks: tuple[str, ...] = ()
    ats_findings: tuple["ATSRisk", ...] = ()


@dataclass(frozen=True)
class ATSRisk:
    """Structured ATS warning with severity and source evidence."""

    code: str
    severity: str
    message: str
    evidence: str


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


def detect_ats_findings(resume: str) -> tuple[ATSRisk, ...]:
    """Return structured ATS risks for review and future document parsers."""
    findings: list[ATSRisk] = []
    lines = resume.splitlines()
    for index, line in enumerate(lines, start=1):
        if "\t" in line:
            findings.append(ATSRisk("columns", "high", "Tab-separated columns may be difficult for ATS parsers to read.", f"Resume line {index}"))
        if line.count("|") >= 2:
            findings.append(ATSRisk("table", "high", "Table-like content may be difficult for ATS parsers to read.", f"Resume line {index}"))
    if re.search(r"!\[[^\]]*\]\([^)]*\)|\[(?:image|photo|logo)\]", resume, re.IGNORECASE):
        findings.append(ATSRisk("image", "medium", "Images may be ignored by ATS parsers.", "Image marker in resume text"))
    return tuple(findings)


def build_tailoring_result(resume: str, job_description: str) -> TailoringResult:
    """Build a safe source-preserving result without inventing candidate facts."""
    requirements = extract_requirements(job_description)
    matches, gaps = match_requirements(resume, requirements)

    tailored_resume = resume.strip()
    ats_risks = detect_ats_risks(resume)
    from app.safety import validate_claims

    validation = validate_claims(
        resume,
        tailored_resume,
        ats_risks=ats_risks,
        ats_findings=detect_ats_findings(resume),
    )
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
    resume_lower = _normalized_match_text(resume)
    resume_lines = resume.splitlines()
    matches = tuple(
        Requirement(
            item.value,
            item.category,
            "matched",
            _evidence_for(resume_lines, item.value),
            item.confidence,
        )
        for item in requirements
        if _requirement_is_supported(item.value, resume_lower, resume_lines)
    )
    matched_values = {_normalized_match_text(requirement.value) for requirement in matches}
    gaps = tuple(
        Requirement(item.value, item.category, "gap", None, item.confidence)
        for item in requirements
        if _normalized_match_text(item.value) not in matched_values
    )
    return matches, gaps


def _normalized_match_text(value: str) -> str:
    return re.sub(r"[^a-z0-9+#]+", " ", value.casefold()).strip()


def _requirement_is_supported(value: str, resume_lower: str, resume_lines: list[str]) -> bool:
    normalized = _normalized_match_text(value)
    candidates = {normalized, _ALIASES.get(normalized, normalized)}
    candidates.update(alias for alias, canonical in _ALIASES.items() if canonical == normalized)
    if any(re.search(rf"\b(?:no|without|not)\s+{re.escape(candidate)}\b", resume_lower) for candidate in candidates):
        return False
    return any(candidate in resume_lower for candidate in candidates)


def _evidence_for(lines: list[str], value: str) -> str:
    normalized = _normalized_match_text(value)
    alias = _ALIASES.get(normalized, normalized)
    aliases = {normalized, alias}
    aliases.update(alias_name for alias_name, canonical in _ALIASES.items() if canonical == normalized)
    for index, line in enumerate(lines, start=1):
        line_lower = _normalized_match_text(line)
        if any(candidate in line_lower for candidate in aliases):
            return f"Resume line {index}: {line.strip()}"
    return f"Found in source resume: {value}"


def detect_ats_risks(resume: str) -> tuple[str, ...]:
    """Analyze resume text for structures that can reduce ATS readability."""
    return _detect_ats_risks(resume)


def build_diff(original: str, tailored: str) -> DiffResult:
    """Create the machine-readable and human-readable comparison result."""
    return _build_diff(original, tailored)


def render_exports(resume: str) -> tuple[ExportResult, ...]:
    """Render supported output formats and report deferred formats explicitly."""
    from app.exporters import render_docx, render_pdf

    try:
        _, docx_content = render_docx(resume)
        docx_export = ExportResult("docx", True, docx_content.hex(), None)
    except Exception as error:
        docx_export = ExportResult("docx", False, None, "DOCX export failed safely.")
    try:
        _, pdf_content = render_pdf(resume)
        pdf_export = ExportResult("pdf", True, pdf_content.hex(), None)
    except Exception:
        pdf_export = ExportResult("pdf", False, None, "PDF export failed safely.")
    return (
        ExportResult("markdown", True, _markdown_export(resume), None),
        docx_export,
        pdf_export,
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
        category = _requirement_category(normalized)
        requirements.append(Requirement(normalized, category, "unmatched", None))
    return tuple(requirements)


def _requirement_category(value: str) -> str:
    lowered = value.casefold()
    if lowered in _SKILL_TERMS or any(character in value for character in "+#./-"):
        return "tool_or_skill"
    if lowered in {"senior", "lead", "manager", "director", "principal"}:
        return "seniority"
    if re.fullmatch(r"\d+", value):
        return "experience_signal"
    return "keyword"


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
