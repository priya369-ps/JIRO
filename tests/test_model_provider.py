import unittest

from app.model_provider import (
    ModelConfig,
    ModelProviderError,
    ModelResponse,
    validate_prompt,
)


class FakeProvider:
    def generate(self, prompt: str, config: ModelConfig) -> ModelResponse:
        validate_prompt(prompt)
        return ModelResponse(
            content=f"generated for {config.model}",
            provider=config.provider,
            model=config.model,
            input_tokens=3,
            output_tokens=4,
            finish_status="stop",
        )


class ModelProviderContractTests(unittest.TestCase):
    def test_config_is_provider_neutral_and_hides_api_key(self) -> None:
        config = ModelConfig(
            provider="byok",
            model="test-model",
            api_key="secret-value",
            options={"temperature": 0},
        )

        self.assertNotIn("secret-value", repr(config))
        self.assertEqual(config.options["temperature"], 0)
        with self.assertRaises(TypeError):
            config.options["new-value"] = True

    def test_fake_provider_implements_generate_contract(self) -> None:
        response = FakeProvider().generate(
            "Rewrite only supported facts.",
            ModelConfig(provider="local", model="llama-test"),
        )

        self.assertEqual(response.content, "generated for llama-test")
        self.assertEqual(
            response.metadata(),
            {
                "provider": "local",
                "model": "llama-test",
                "request_id": None,
                "input_tokens": 3,
                "output_tokens": 4,
                "finish_status": "stop",
            },
        )

    def test_invalid_configuration_and_prompt_fail_clearly(self) -> None:
        with self.assertRaisesRegex(ModelProviderError, "Unsupported model provider"):
            ModelConfig(provider="unsupported", model="test-model")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ModelProviderError, "cannot be empty"):
            validate_prompt(" \n")
        with self.assertRaisesRegex(ModelProviderError, "cannot be negative"):
            ModelResponse("text", "groq", "test-model", input_tokens=-1)


if __name__ == "__main__":
    unittest.main()
