import unittest

from app.ingest import IngestionError, ingest_file, ingest_text
from app.model_provider import LocalProvider, ModelConfig
from app.privacy import PrivacyError, redact_mapping, remove_sensitive_keys, sanitize_filename


class PrivacyTests(unittest.TestCase):
    def test_filename_policy_rejects_paths_hidden_files_and_controls(self) -> None:
        with self.assertRaisesRegex(PrivacyError, "without a path"):
            sanitize_filename("nested\\resume.txt")
        with self.assertRaisesRegex(PrivacyError, "Hidden"):
            sanitize_filename(".resume.txt")
        with self.assertRaisesRegex(PrivacyError, "unsafe characters"):
            sanitize_filename("resume\n.txt")

    def test_ingestion_keeps_source_in_memory_without_persisting_it(self) -> None:
        document = ingest_text("Sensitive resume content", source_name="resume.txt")

        self.assertEqual(document.original_text, "Sensitive resume content")
        self.assertEqual(document.normalized_text, "Sensitive resume content")
        self.assertFalse(hasattr(document, "path"))

    def test_diagnostics_redact_and_requests_remove_secret_options(self) -> None:
        values = {"temperature": 0, "api_key": "secret", "session_id": "session"}

        self.assertEqual(redact_mapping(values)["api_key"], "[REDACTED]")
        self.assertNotIn("api_key", remove_sensitive_keys(values))

        calls: list[dict[str, object]] = []

        def transport(endpoint, payload, headers):
            calls.append(payload)
            return {"choices": [{"message": {"content": "local"}}]}

        LocalProvider(transport=transport).generate(
            "safe prompt",
            ModelConfig(
                provider="local",
                model="test-model",
                options={"api_key": "secret", "temperature": 0},
            ),
        )

        self.assertNotIn("api_key", calls[0])
        self.assertNotIn("secret", repr(calls[0]))
        self.assertEqual(calls[0]["temperature"], 0)

    def test_existing_ingestion_errors_remain_safe(self) -> None:
        with self.assertRaisesRegex(IngestionError, "unsafe characters"):
            ingest_file("resume\n.txt", b"content")
        with self.assertRaisesRegex(IngestionError, "cannot be empty"):
            ingest_text(" \n")


if __name__ == "__main__":
    unittest.main()
