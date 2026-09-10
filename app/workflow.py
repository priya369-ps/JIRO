"""Ephemeral workflow state returned to a frontend without retaining source data."""

from typing import Literal

from app.outputs import TailoringResult


WorkflowState = Literal["input", "processing", "review", "export"]


def input_workflow_state() -> dict[str, object]:
    return {
        "state": "input",
        "provider_configured": False,
        "privacy_mode": "ephemeral",
    }


def review_workflow_state(result: TailoringResult) -> dict[str, object]:
    return {
        "state": "review",
        "provider_configured": False,
        "privacy_mode": "ephemeral",
        "validation_status": result.validation.status,
        "warnings_present": bool(result.validation.warnings),
        "export_blocked": result.validation.export_blocked,
        "available_exports": [item.format for item in result.exports if item.available],
    }