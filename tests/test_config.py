import unittest

from app.config import (
    DEFAULT_GROQ_MODEL,
    DEFAULT_OLLAMA_ENDPOINT,
    ConfigurationError,
    load_settings,
)


class ConfigurationTests(unittest.TestCase):
    def test_defaults_are_non_secret_and_operationally_complete(self) -> None:
        settings = load_settings({})

        self.assertEqual(settings.default_provider, "groq")
        self.assertEqual(settings.default_model, DEFAULT_GROQ_MODEL)
        self.assertEqual(settings.ollama_endpoint, DEFAULT_OLLAMA_ENDPOINT)
        self.assertEqual(settings.public_metadata()["privacy_mode"], "ephemeral")
        self.assertNotIn("api_key", settings.public_metadata())

    def test_environment_overrides_are_validated_and_bounded(self) -> None:
        settings = load_settings(
            {
                "JIRO_DEFAULT_PROVIDER": "local",
                "JIRO_GROQ_MODEL": "custom-model",
                "JIRO_OLLAMA_ENDPOINT": "http://localhost:11434",
                "JIRO_PROVIDER_TIMEOUT_SECONDS": "500",
            }
        )

        self.assertEqual(settings.default_provider, "local")
        self.assertEqual(settings.default_model, "")
        self.assertEqual(settings.provider_timeout_seconds, 120.0)

    def test_invalid_environment_returns_safe_configuration_errors(self) -> None:
        invalid_values = (
            ({"JIRO_DEFAULT_PROVIDER": "unknown"}, "DEFAULT_PROVIDER"),
            ({"JIRO_GROQ_MODEL": ""}, "GROQ_MODEL"),
            ({"JIRO_OLLAMA_ENDPOINT": "file:///tmp/model"}, "OLLAMA_ENDPOINT"),
            ({"JIRO_PROVIDER_TIMEOUT_SECONDS": "invalid"}, "TIMEOUT_SECONDS"),
        )
        for values, expected in invalid_values:
            with self.subTest(values=values):
                with self.assertRaisesRegex(ConfigurationError, expected):
                    load_settings(values)


if __name__ == "__main__":
    unittest.main()
