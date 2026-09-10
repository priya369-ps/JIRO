import unittest

from fastapi.testclient import TestClient

from app.ingest import IngestionError, ingest_file, ingest_text
from app.main import app


class IngestionTests(unittest.TestCase):
    def test_text_preserves_source_and_normalizes_whitespace(self) -> None:
        source = "Name\r\n\r\n\r\nExperience   \r\n"

        document = ingest_text(source, source_name="resume-paste")

        self.assertEqual(document.original_text, source)
        self.assertEqual(document.normalized_text, "Name\n\nExperience")
        self.assertEqual(document.source_name, "resume-paste")
        self.assertEqual(document.source_type, "text")

    def test_text_rejects_empty_input(self) -> None:
        with self.assertRaisesRegex(IngestionError, "cannot be empty"):
            ingest_text(" \n\t")

    def test_file_rejects_unsupported_type_and_paths(self) -> None:
        with self.assertRaisesRegex(IngestionError, "Unsupported file type"):
            ingest_file("resume.html", b"<p>Resume</p>")
        with self.assertRaisesRegex(IngestionError, "without a path"):
            ingest_file("folder/resume.txt", b"Resume")

    def test_txt_file_is_decoded(self) -> None:
        document = ingest_file("resume.txt", b"Name\r\nSkills\r\n")

        self.assertEqual(document.original_text, "Name\r\nSkills\r\n")
        self.assertEqual(document.normalized_text, "Name\nSkills")

    def test_text_endpoint_accepts_provider_configuration(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/ingest/text",
                json={
                    "text": "Resume\r\n\r\nSkills",
                    "provider": "local",
                    "model": "llama3.2",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["normalized_text"], "Resume\n\nSkills")

    def test_text_endpoint_rejects_unknown_provider(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/ingest/text",
                json={"text": "Resume", "provider": "unknown"},
            )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()