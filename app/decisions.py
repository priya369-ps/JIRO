"""Explicit, reversible product decisions and conflict-resolution priorities."""

from dataclasses import asdict, dataclass
from typing import Final


@dataclass(frozen=True)
class ProductDecisions:
    """Current milestone choices exposed without source data or credentials."""

    resume_profiles: str = "single_ephemeral_profile"
    diff_granularity: str = "section_and_line"
    shared_key_rate_limit: str = "bounded_per_session"
    frontend: str = "fastapi_text_first_nextjs_future"
    export_engine: str = "markdown_now_docx_pdf_deferred"

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


CONFLICT_PRIORITIES: Final[tuple[str, ...]] = (
    "preserve_user_data",
    "preserve_provider_isolation",
    "preserve_no_fabrication",
    "make_smallest_affected_change",
    "add_regression_test",
)


def resolve_conflict(*concerns: str) -> tuple[str, ...]:
    """Return recognized concerns in the mandated safety-first order."""
    concern_set = set(concerns)
    return tuple(priority for priority in CONFLICT_PRIORITIES if priority in concern_set)