import unittest

from app.model_provider import (
    BYOKProvider,
    GroqProvider,
    LocalProvider,
    ModelConfig,
    ModelProviderError,
    ModelResponse,
    ProviderConfigurationError,
    ProviderRequestError,
    SessionRateLimiter,
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

    def test_groq_uses_server_key_and_openai_compatible_payload(self) -> None:
        calls: list[tuple[str, dict[str, object], dict[str, str]]] = []

        def transport(endpoint: str, payload: dict[str, object], headers: dict[str, str]) -> dict[str, object]:
            calls.append((endpoint, payload, headers))
            return {"id": "request-1", "choices": [{"message": {"content": "result"}, "finish_reason": "stop"}]}

        provider = GroqProvider(transport=transport, rate_limiter=SessionRateLimiter(limit=1))
        response = provider.generate(
            "Use only source facts.",
            ModelConfig(provider="groq", model="openai/gpt-oss-120b", api_key="server-key"),
        )

        self.assertEqual(response.content, "result")
        self.assertEqual(calls[0][0], "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(calls[0][2]["Authorization"], "Bearer server-key")
        self.assertNotIn("server-key", repr(response))

    def test_byok_requires_supported_upstream_and_local_never_requires_shared_key(self) -> None:
        transport = lambda endpoint, payload, headers: {
            "choices": [{"message": {"content": "local result"}}]
        }
        with self.assertRaisesRegex(ProviderConfigurationError, "supported upstream"):
            BYOKProvider(transport=transport).generate(
                "prompt",
                ModelConfig(provider="byok", model="test", api_key="user-key"),
            )

        response = LocalProvider(transport=transport).generate(
            "prompt",
            ModelConfig(provider="local", model="llama-test"),
        )
        self.assertEqual(response.content, "local result")

    def test_rate_limit_is_bounded_per_session(self) -> None:
        limiter = SessionRateLimiter(limit=1)
        limiter.check("session-a")
        with self.assertRaisesRegex(ProviderRequestError, "rate limit"):
            limiter.check("session-a")
        limiter.check("session-b")


if __name__ == "__main__":
    unittest.main()
