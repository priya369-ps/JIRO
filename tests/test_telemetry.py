import logging
import unittest
from io import StringIO

from fastapi.testclient import TestClient

from app.main import app
from app.telemetry import SafeEvent, SafeEventLogger


class TelemetryTests(unittest.TestCase):
    def test_safe_event_allowlist_excludes_sensitive_fields(self) -> None:
        event = SafeEvent(
            request_id="request-1",
            route="/tailor",
            stage="http",
            provider="local",
            model="test-model",
        )

        values = event.as_dict()
        self.assertEqual(values["request_id"], "request-1")
        self.assertNotIn("resume", values)
        self.assertNotIn("prompt", values)
        self.assertNotIn("api_key", values)

    def test_logger_does_not_emit_sensitive_event_content(self) -> None:
        stream = StringIO()
        logger = logging.getLogger("test-jiro-telemetry")
        logger.handlers.clear()
        logger.addHandler(logging.StreamHandler(stream))
        logger.setLevel(logging.INFO)

        SafeEventLogger(logger).emit(SafeEvent("request-1", "/tailor", "http"))

        self.assertNotIn("resume", stream.getvalue())
        self.assertNotIn("prompt", stream.getvalue())
        self.assertNotIn("secret", stream.getvalue())

    def test_api_adds_request_id_header(self) -> None:
        with TestClient(app) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers.get("x-request-id"))


if __name__ == "__main__":
    unittest.main()
