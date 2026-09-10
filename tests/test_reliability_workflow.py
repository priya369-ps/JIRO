import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.reliability import MAX_REQUEST_BODY_BYTES, bounded_timeout, cors_origins


class ReliabilityWorkflowTests(unittest.TestCase):
    def test_timeout_is_positive_and_bounded(self) -> None:
        self.assertEqual(bounded_timeout(30), 30)
        self.assertEqual(bounded_timeout(500), 120)
        with self.assertRaisesRegex(ValueError, "positive"):
            bounded_timeout(0)

    def test_cors_defaults_are_explicit(self) -> None:
        self.assertEqual(
            cors_origins(),
            ["http://localhost:3000", "http://127.0.0.1:3000"],
        )

    def test_oversized_request_is_rejected(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/ingest/text",
                content=b"x" * (MAX_REQUEST_BODY_BYTES + 1),
                headers={"content-type": "application/json"},
            )

        self.assertEqual(response.status_code, 413)
        self.assertNotIn("x" * 100, response.text)

    def test_workflow_state_is_ephemeral_and_exposes_review_controls(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/tailor",
                json={"resume": "Python developer", "job_description": "Python and Kubernetes"},
            )

        workflow = response.json()["workflow"]
        self.assertEqual(workflow["state"], "review")
        self.assertEqual(workflow["privacy_mode"], "ephemeral")
        self.assertIn("Python", response.json()["matches"][0]["value"])
        self.assertIn("markdown", workflow["available_exports"])


if __name__ == "__main__":
    unittest.main()