import unittest

from app.safety import (
    NO_FABRICATION_SYSTEM_PROMPT,
    build_rewrite_prompt,
    find_unsupported_claims,
    validate_claims,
)


class SafetyTests(unittest.TestCase):
    def test_prompt_declares_source_authority_and_structured_output(self) -> None:
        prompt = build_rewrite_prompt(
            "Python developer with FastAPI experience.",
            "Looking for Python and Kubernetes experience.",
        )

        self.assertIn(NO_FABRICATION_SYSTEM_PROMPT, prompt)
        self.assertIn("only authority for candidate facts", prompt)
        self.assertIn('"unsupported_claims"', prompt)
        self.assertIn("Kubernetes", prompt)

    def test_validator_flags_unsupported_explicit_claims(self) -> None:
        findings = find_unsupported_claims(
            "Python developer at Example LLC from 2021 to 2022.",
            "Senior Python developer at Acme Inc. from 2021 to 2025, serving 40% more users.",
        )

        self.assertEqual(
            {(finding.category, finding.value) for finding in findings},
            {
                ("company", "Acme Inc."),
                ("date", "2025"),
                ("metric", "40%"),
                ("title", "Senior"),
            },
        )

    def test_failed_validation_blocks_export(self) -> None:
        validation = validate_claims(
            "Python developer.",
            "Python developer at Acme Inc. in 2025.",
        )

        self.assertEqual(validation.status, "failed")
        self.assertTrue(validation.export_blocked)
        self.assertTrue(any("Unsupported company" in warning for warning in validation.warnings))

    def test_source_preserving_text_passes_validation(self) -> None:
        validation = validate_claims("Python developer in 2025.", "Python developer in 2025.")

        self.assertEqual(validation.status, "passed")
        self.assertFalse(validation.export_blocked)

    def test_validator_flags_unsupported_skill_and_responsibility(self) -> None:
        findings = find_unsupported_claims(
            "Python developer.",
            "Python and Kubernetes developer.\n- Managed a team of 12 engineers.",
        )

        self.assertIn(("skill", "Kubernetes"), {(item.category, item.value) for item in findings})
        self.assertIn(
            ("responsibility", "- Managed a team of 12 engineers."),
            {(item.category, item.value) for item in findings},
        )


if __name__ == "__main__":
    unittest.main()
