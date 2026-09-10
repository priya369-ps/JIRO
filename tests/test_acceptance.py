import unittest

from app.ingest import MAX_INPUT_BYTES, IngestionError, ingest_file
from app.model_provider import LocalProvider, ModelConfig, ProviderRequestError
from app.outputs import Requirement
from app.pipeline import DeterministicTailoringPipeline


class AcceptanceGateTests(unittest.TestCase):
    def test_malformed_and_oversized_files_fail_without_content_echo(self) -> None:
        with self.assertRaisesRegex(IngestionError, "UTF-8") as malformed:
            ingest_file("resume.txt", b"\xff\xfe")
        self.assertNotIn("\\xff", str(malformed.exception))

        with self.assertRaisesRegex(IngestionError, "5 MB") as oversized:
            ingest_file("resume.txt", b"x" * (MAX_INPUT_BYTES + 1))
        self.assertNotIn("x" * 100, str(oversized.exception))

    def test_provider_timeout_is_safe_and_does_not_fallback(self) -> None:
        def timeout_transport(endpoint, payload, headers):
            raise TimeoutError("private provider detail")

        with self.assertRaisesRegex(ProviderRequestError, "request failed") as error:
            LocalProvider(transport=timeout_transport).generate(
                "prompt",
                ModelConfig(provider="local", model="local-test"),
            )
        self.assertNotIn("private provider detail", str(error.exception))

    def test_pipeline_blocks_export_after_unsupported_claim(self) -> None:
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

        self.assertEqual(result.validation.status, "failed")
        self.assertTrue(result.validation.export_blocked)
        self.assertEqual(result.exports, ())

    def test_injected_provider_results_are_serializable_without_secrets(self) -> None:
        response = LocalProvider(
            transport=lambda endpoint, payload, headers: {
                "id": "safe-id",
                "choices": [{"message": {"content": "output"}}],
            }
        ).generate(
            "prompt",
            ModelConfig(provider="local", model="local-test", api_key="secret"),
        )

        serialized = response.metadata()
        self.assertNotIn("secret", repr(serialized))
        self.assertEqual(serialized["request_id"], "safe-id")


if __name__ == "__main__":
    unittest.main()
