import unittest

from app.gates import (
    DefinitionOfDoneReport,
    GateResult,
    build_definition_of_done,
    run_acceptance_gates,
)


class QualityGateTests(unittest.TestCase):
    def test_acceptance_gates_pass_without_network_or_credentials(self) -> None:
        gates = run_acceptance_gates()

        self.assertGreaterEqual(len(gates), 7)
        self.assertTrue(all(gate.passed for gate in gates), gates)

    def test_definition_of_done_reports_missing_evidence(self) -> None:
        report = build_definition_of_done(
            (GateResult("privacy", True, "ok"),),
            focused_tests_passed=False,
            documentation_updated=False,
        )

        self.assertIsInstance(report, DefinitionOfDoneReport)
        self.assertFalse(report.passed)
        self.assertEqual(
            {failure.name for failure in report.failures},
            {"focused-tests", "documentation"},
        )

    def test_definition_of_done_passes_with_all_evidence(self) -> None:
        report = build_definition_of_done(
            (GateResult("privacy", True, "ok"), GateResult("safety", True, "ok")),
            focused_tests_passed=True,
            documentation_updated=True,
        )

        self.assertTrue(report.passed)
        self.assertEqual(report.failures, ())


if __name__ == "__main__":
    unittest.main()
