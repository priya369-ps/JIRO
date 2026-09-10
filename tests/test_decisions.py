import unittest

from app.decisions import CONFLICT_PRIORITIES, ProductDecisions, resolve_conflict


class ProductDecisionTests(unittest.TestCase):
    def test_decisions_are_explicit_and_serializable(self) -> None:
        decisions = ProductDecisions().as_dict()

        self.assertEqual(decisions["resume_profiles"], "single_ephemeral_profile")
        self.assertEqual(decisions["diff_granularity"], "section_and_line")
        self.assertEqual(decisions["export_engine"], "markdown_now_docx_pdf_deferred")

    def test_conflicts_follow_safety_first_priority(self) -> None:
        self.assertEqual(
            resolve_conflict(
                "add_regression_test",
                "preserve_no_fabrication",
                "preserve_user_data",
            ),
            (
                "preserve_user_data",
                "preserve_no_fabrication",
                "add_regression_test",
            ),
        )
        self.assertEqual(resolve_conflict("unknown"), ())
        self.assertEqual(CONFLICT_PRIORITIES[-1], "add_regression_test")


if __name__ == "__main__":
    unittest.main()