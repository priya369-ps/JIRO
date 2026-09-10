import unittest

from app.architecture import ModelResponse
from app.pipeline import DefaultInputParser, DeterministicTailoringPipeline, build_default_pipeline


class ArchitectureTests(unittest.TestCase):
    def test_default_parser_preserves_ingestion_contract(self) -> None:
        parser = DefaultInputParser()

        document = parser.parse_text("Resume\nSkills", source_name="resume")

        self.assertEqual(document.source_name, "resume")
        self.assertEqual(document.original_text, "Resume\nSkills")
        self.assertEqual(document.normalized_text, "Resume\nSkills")

    def test_default_pipeline_exposes_tailoring_pipeline_contract(self) -> None:
        pipeline = build_default_pipeline()

        result = pipeline.run("Python developer", "Python and Kubernetes")

        self.assertIsInstance(pipeline, DeterministicTailoringPipeline)
        self.assertEqual(result.tailored_resume, "Python developer")
        self.assertEqual([item.value for item in result.matches], ["Python"])
        self.assertEqual([item.value for item in result.gaps], ["Kubernetes"])

    def test_model_response_is_provider_neutral(self) -> None:
        response = ModelResponse(
            content="generated content",
            provider="local",
            model="llama3.2",
            finish_status="stop",
        )

        self.assertEqual(response.provider, "local")
        self.assertEqual(response.model, "llama3.2")
        self.assertEqual(response.finish_status, "stop")
        self.assertIsNone(response.request_id)


if __name__ == "__main__":
    unittest.main()
