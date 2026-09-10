import unittest

from fastapi.testclient import TestClient

import app.main as main
from app.outputs import ExportResult, Requirement
from app.pipeline import DeterministicTailoringPipeline


class FakeRewritePipeline(DeterministicTailoringPipeline):
    """Deterministic fake-provider equivalent for API workflow tests."""

    def __init__(self, rewritten_resume: str) -> None:
        self.rewritten_resume = rewritten_resume

    def run(self, resume: str, job_description: str):
        class Analyzer:
            def analyze(self, description: str):
                return (Requirement("Python", "tool_or_skill", "unmatched"),)

        class Matcher:
            def match(self, source: str, requirements):
                return requirements, ()

        class Rewriter:
            def __init__(self, output: str) -> None:
                self.output = output

            def rewrite(self, source: str, description: str) -> str:
                return self.output

        return DeterministicTailoringPipeline(
            analyzer=Analyzer(),
            matcher=Matcher(),
            rewriter=Rewriter(self.rewritten_resume),
        ).run(resume, job_description)


class EndToEndWorkflowTests(unittest.TestCase):
    def test_successful_tailoring_review_and_exports(self) -> None:
        original = main.tailoring_pipeline
        main.tailoring_pipeline = FakeRewritePipeline("Python developer")
        try:
            with TestClient(main.app) as client:
                response = client.post(
                    "/tailor",
                    json={"resume": "Developer with Python", "job_description": "Python role"},
                )
        finally:
            main.tailoring_pipeline = original

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["workflow"]["state"], "review")
        self.assertEqual(body["validation"]["status"], "passed")
        self.assertTrue({item["format"] for item in body["exports"]} >= {"markdown", "docx", "pdf"})

    def test_unsupported_claim_is_visible_and_blocks_export(self) -> None:
        original = main.tailoring_pipeline
        main.tailoring_pipeline = FakeRewritePipeline("Python developer at Acme Inc. in 2025.")
        try:
            with TestClient(main.app) as client:
                response = client.post(
                    "/tailor",
                    json={"resume": "Developer with Python", "job_description": "Python role"},
                )
        finally:
            main.tailoring_pipeline = original

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["validation"]["status"], "failed")
        self.assertTrue(body["workflow"]["export_blocked"])
        self.assertEqual(body["exports"], [])
        self.assertTrue(any("Unsupported company" in warning for warning in body["validation"]["warnings"]))

    def test_file_input_reaches_review_workflow(self) -> None:
        with TestClient(main.app) as client:
            response = client.post(
                "/ingest/file",
                files={"file": ("resume.txt", b"Python developer", "text/plain")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workflow"]["state"], "input")
        self.assertEqual(response.json()["normalized_text"], "Python developer")


if __name__ == "__main__":
    unittest.main()
