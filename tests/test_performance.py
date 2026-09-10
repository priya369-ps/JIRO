import unittest

from app.performance import PerformanceMetrics
from app.pipeline import DeterministicTailoringPipeline
from app.privacy import MAX_TEXT_BYTES, PrivacyError, ensure_text_input
from app.outputs import ExportResult


class PerformanceTests(unittest.TestCase):
    def test_pipeline_reports_all_stage_timings_and_peak_memory(self) -> None:
        class MarkdownExporter:
            def export(self, resume: str):
                return (ExportResult("markdown", True, resume, None),)

        result = DeterministicTailoringPipeline(exporter=MarkdownExporter()).run(
            "Python developer with SQL experience",
            "Build Python services with SQL",
        )

        self.assertIsInstance(result.performance, PerformanceMetrics)
        metrics = result.performance
        assert metrics is not None
        for stage in ("input_parsing", "analysis", "matching", "provider", "validation", "export"):
            self.assertGreaterEqual(getattr(metrics, f"{stage}_ms"), 0)
        self.assertGreaterEqual(metrics.total_ms, 0)
        self.assertGreater(metrics.peak_memory_bytes, 0)

    def test_text_input_has_a_bounded_utf8_size(self) -> None:
        with self.assertRaisesRegex(PrivacyError, "5 MB"):
            ensure_text_input("x" * (MAX_TEXT_BYTES + 1), label="Resume")


if __name__ == "__main__":
    unittest.main()