import unittest

from app.history import EphemeralHistory, HistoryError
from app.outputs import build_tailoring_result


class HistoryTests(unittest.TestCase):
    def test_history_requires_explicit_opt_in(self) -> None:
        history = EphemeralHistory()
        result = build_tailoring_result("Python developer", "Python")

        with self.assertRaisesRegex(HistoryError, "history_opt_in"):
            history.save("profile", result, privacy_mode="ephemeral")

    def test_opted_in_versions_can_be_deleted(self) -> None:
        history = EphemeralHistory()
        result = build_tailoring_result("Python developer", "Python")

        version = history.save("profile", result, privacy_mode="history_opt_in")
        self.assertEqual(len(history.list("profile", privacy_mode="history_opt_in")), 1)
        self.assertEqual(version.validation_status, "passed")

        history.delete("profile", privacy_mode="history_opt_in")
        self.assertEqual(history.list("profile", privacy_mode="history_opt_in"), ())


if __name__ == "__main__":
    unittest.main()
