import unittest

from app.architecture import ModelResponse
from app.outputs import ExportResult, Requirement, ValidationResult
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

    def test_pipeline_runs_injectable_processing_stages_in_order(self) -> None:
        calls: list[str] = []

        class Analyzer:
            def analyze(self, job_description: str):
                calls.append("analyze")
                return (Requirement("Python", "keyword", "unmatched"),)

        class Matcher:
            def match(self, resume: str, requirements):
                calls.append("match")
                return requirements, ()

        class Rewriter:
            def rewrite(self, resume: str, job_description: str) -> str:
                calls.append("rewrite")
                return resume + "\nTailored"

        class Validator:
            def validate(self, original_resume: str, tailored_resume: str):
                calls.append("validate")
                return ValidationResult("passed", (), False)

        class Formatter:
            def format(self, resume: str) -> str:
                calls.append("format")
                return resume + "\nFormatted"

        class Exporter:
            def export(self, resume: str):
                calls.append("export")
                return (ExportResult("markdown", True, resume, None),)

        result = DeterministicTailoringPipeline(
            analyzer=Analyzer(),
            matcher=Matcher(),
            rewriter=Rewriter(),
            validator=Validator(),
            formatter=Formatter(),
            exporter=Exporter(),
        ).run("Source", "Job")

        self.assertEqual(calls, ["analyze", "match", "rewrite", "format", "validate", "export"])
        self.assertEqual(result.tailored_resume, "Source\nTailored\nFormatted")
        self.assertEqual(result.exports[0].content, result.tailored_resume)


if __name__ == "__main__":
    unittest.main()
