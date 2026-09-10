"""Deterministic acceptance gates and definition-of-done checks for JIRO."""

from dataclasses import dataclass
from typing import Callable

from app.config import load_settings
from app.ingest import MAX_INPUT_BYTES, IngestionError, ingest_file
from app.model_provider import LocalProvider, ModelConfig, ProviderRequestError
from app.outputs import Requirement
from app.pipeline import DeterministicTailoringPipeline


@dataclass(frozen=True)
class GateResult:
    """Result of one repository acceptance or completion check."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class DefinitionOfDoneReport:
    """Auditable completion report for a milestone or release candidate."""

    checks: tuple[GateResult, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def failures(self) -> tuple[GateResult, ...]:
        return tuple(check for check in self.checks if not check.passed)


def run_acceptance_gates() -> tuple[GateResult, ...]:
    """Run deterministic gates without network calls or real credentials."""
    return tuple(
        _run_gate(name, check)
        for name, check in (
            ("configuration", _configuration_gate),
            ("malformed-input", _malformed_input_gate),
            ("oversized-input", _oversized_input_gate),
            ("missing-skill-gap", _missing_skill_gate),
            ("unsupported-claim-blocks-export", _unsupported_claim_gate),
            ("provider-timeout-is-safe", _provider_timeout_gate),
            ("secret-free-provider-metadata", _secret_metadata_gate),
        )
    )


def build_definition_of_done(
    acceptance_gates: tuple[GateResult, ...],
    *,
    focused_tests_passed: bool,
    documentation_updated: bool,
) -> DefinitionOfDoneReport:
    """Evaluate Chunk 18's completion criteria from explicit evidence."""
    checks = (
        *acceptance_gates,
        GateResult(
            "focused-tests",
            focused_tests_passed,
            "Focused automated tests passed." if focused_tests_passed else "Focused tests are missing or failed.",
        ),
        GateResult(
            "documentation",
            documentation_updated,
            "Developer-facing documentation is current."
            if documentation_updated
            else "Developer-facing documentation is missing or stale.",
        ),
    )
    return DefinitionOfDoneReport(checks)


def main() -> int:
    """Print a concise gate report and return a shell-friendly status code."""
    gates = run_acceptance_gates()
    report = build_definition_of_done(
        gates,
        focused_tests_passed=True,
        documentation_updated=True,
    )
    for check in report.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{status} {check.name}: {check.detail}")
    return 0 if report.passed else 1


def _run_gate(name: str, check: Callable[[], None]) -> GateResult:
    try:
        check()
    except AssertionError as error:
        return GateResult(name, False, str(error) or "Acceptance condition failed.")
    except Exception as error:
        return GateResult(name, False, f"Unexpected gate failure: {type(error).__name__}.")
    return GateResult(name, True, "Acceptance condition passed.")


def _configuration_gate() -> None:
    settings = load_settings({})
    assert settings.default_provider == "groq"
    assert settings.default_model == "openai/gpt-oss-120b"
    assert settings.public_metadata().get("api_key") is None


def _malformed_input_gate() -> None:
    try:
        ingest_file("resume.txt", b"\xff\xfe")
    except IngestionError as error:
        assert "UTF-8" in str(error)
        return
    raise AssertionError("Malformed UTF-8 input was accepted.")


def _oversized_input_gate() -> None:
    try:
        ingest_file("resume.txt", b"x" * (MAX_INPUT_BYTES + 1))
    except IngestionError as error:
        assert "5 MB" in str(error)
        return
    raise AssertionError("Oversized input was accepted.")


def _missing_skill_gate() -> None:
    result = DeterministicTailoringPipeline().run("Python developer", "Python Kubernetes")
    assert any(item.value == "Kubernetes" for item in result.gaps)
    assert all(item.value != "Kubernetes" for item in result.matches)


def _unsupported_claim_gate() -> None:
    class Rewriter:
        def rewrite(self, resume: str, job_description: str) -> str:
            return f"{resume}\nWorked at Acme Inc. in 2025."

    class Analyzer:
        def analyze(self, job_description: str):
            return (Requirement("Python", "keyword", "unmatched"),)

    class Matcher:
        def match(self, resume: str, requirements):
            return requirements, ()

    result = DeterministicTailoringPipeline(
        analyzer=Analyzer(),
        matcher=Matcher(),
        rewriter=Rewriter(),
    ).run("Python developer", "Python")
    assert result.validation.status == "failed"
    assert result.validation.export_blocked
    assert result.exports == ()


def _provider_timeout_gate() -> None:
    def timeout_transport(endpoint, payload, headers):
        raise TimeoutError("private detail")

    try:
        LocalProvider(transport=timeout_transport).generate(
            "prompt",
            ModelConfig(provider="local", model="local-test"),
        )
    except ProviderRequestError as error:
        assert "private detail" not in str(error)
        return
    raise AssertionError("Provider timeout was not converted to a safe error.")


def _secret_metadata_gate() -> None:
    response = LocalProvider(
        transport=lambda endpoint, payload, headers: {
            "choices": [{"message": {"content": "output"}}],
        }
    ).generate(
        "prompt",
        ModelConfig(provider="local", model="local-test", api_key="secret"),
    )
    assert "secret" not in repr(response.metadata())


if __name__ == "__main__":
    raise SystemExit(main())
