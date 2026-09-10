"""Explicit opt-in, process-local resume versioning with no durable persistence."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.outputs import TailoringResult


class HistoryError(ValueError):
    """Raised when history is requested outside an explicit opt-in mode."""


@dataclass(frozen=True)
class ResumeVersion:
    version_id: str
    created_at: str
    tailored_resume: str
    validation_status: str
    warnings: tuple[str, ...]


class EphemeralHistory:
    """Opt-in in-memory versions that disappear when the process ends."""

    def __init__(self) -> None:
        self._versions: dict[str, list[ResumeVersion]] = {}

    def save(self, profile_id: str, result: TailoringResult, *, privacy_mode: str) -> ResumeVersion:
        if privacy_mode != "history_opt_in":
            raise HistoryError("History requires explicit history_opt_in mode.")
        version = ResumeVersion(
            version_id=str(uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            tailored_resume=result.tailored_resume,
            validation_status=result.validation.status,
            warnings=result.validation.warnings,
        )
        self._versions.setdefault(profile_id, []).append(version)
        return version

    def list(self, profile_id: str, *, privacy_mode: str) -> tuple[ResumeVersion, ...]:
        if privacy_mode != "history_opt_in":
            raise HistoryError("History requires explicit history_opt_in mode.")
        return tuple(self._versions.get(profile_id, ()))

    def delete(self, profile_id: str, *, privacy_mode: str) -> None:
        if privacy_mode != "history_opt_in":
            raise HistoryError("History requires explicit history_opt_in mode.")
        self._versions.pop(profile_id, None)
