import unittest

from fastapi.testclient import TestClient

import app.main as main
from app.errors import public_error
from app.model_provider import ProviderRequestError


class ErrorHandlingTests(unittest.TestCase):
    def test_public_error_uses_stable_safe_shape(self) -> None:
        error = public_error("provider", "Model provider request failed.")

        self.assertEqual(error.status_code, 502)
        self.assertEqual(error.payload.model_dump(), {
            "detail": "Model provider request failed.",
            "category": "provider",
        })

    def test_provider_exception_does_not_echo_private_detail(self) -> None:
        original = main.tailoring_pipeline

        class FailingPipeline:
            def run(self, resume: str, job_description: str):
                raise ProviderRequestError("private prompt and resume content")

        main.tailoring_pipeline = FailingPipeline()
        try:
            with TestClient(main.app) as client:
                response = client.post(
                    "/tailor",
                    json={"resume": "Python developer", "job_description": "Python"},
                )
        finally:
            main.tailoring_pipeline = original

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {
            "detail": "private prompt and resume content",
            "category": "provider",
        })

    def test_unexpected_exception_returns_generic_message(self) -> None:
        original = main.tailoring_pipeline

        class FailingPipeline:
            def run(self, resume: str, job_description: str):
                raise RuntimeError("private source content")

        main.tailoring_pipeline = FailingPipeline()
        try:
            with TestClient(main.app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/tailor",
                    json={"resume": "Python developer", "job_description": "Python"},
                )
        finally:
            main.tailoring_pipeline = original

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "The request could not be completed safely.")
        self.assertNotIn("private source content", response.text)


if __name__ == "__main__":
    unittest.main()
