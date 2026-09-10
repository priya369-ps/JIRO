import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.outputs import build_tailoring_result


class TailoringOutputTests(unittest.TestCase):
    def test_result_contains_outputs_without_changing_source_facts(self) -> None:
        result = build_tailoring_result(
            "Alex Developer\nPython and FastAPI experience.",
            "Build APIs with Python and Kubernetes.",
        )

        self.assertEqual(result.tailored_resume, "Alex Developer\nPython and FastAPI experience.")
        self.assertEqual([item.value for item in result.matches], ["Python"])
        self.assertEqual([item.value for item in result.gaps], ["Build", "APIs", "Kubernetes"])
        self.assertFalse(result.diff.changed)
        self.assertIn("No source text was changed.", result.diff.summary)
        self.assertEqual(result.validation.status, "passed")
        self.assertFalse(result.validation.export_blocked)
        self.assertTrue(result.exports[0].available)
        self.assertEqual(result.exports[0].format, "markdown")
        self.assertFalse(result.exports[1].available)
        self.assertFalse(result.exports[2].available)

    def test_tailor_endpoint_returns_serializable_output_contract(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/tailor",
                json={
                    "resume": "Name\nPython developer",
                    "job_description": "Python and Docker",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["tailored_resume"], "Name\nPython developer")
        self.assertIn("job_requirements", body)
        self.assertIn("matches", body)
        self.assertIn("gaps", body)
        self.assertIn("validation", body)
        self.assertIn("diff", body)
        self.assertIn("exports", body)
        self.assertEqual(body["validation"]["status"], "passed")
        self.assertTrue(body["exports"][0]["available"])

    def test_tailor_endpoint_rejects_empty_source_input(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/tailor",
                json={"resume": "", "job_description": "Python"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot be empty", response.json()["detail"])

    def test_ats_risks_are_reported_without_changing_source(self) -> None:
        resume = "Name\nPython\tFastAPI\n| Skills | Python |\n[image]"

        result = build_tailoring_result(resume, "Python and FastAPI")

        self.assertEqual(result.tailored_resume, resume)
        self.assertEqual(
            result.validation.ats_risks,
            (
                "tab-separated columns may be difficult for ATS parsers to read",
                "table-like content may be difficult for ATS parsers to read",
                "images may be ignored by ATS parsers",
            ),
        )
        self.assertTrue(all("ATS risk:" in warning for warning in result.validation.warnings[1:]))

    def test_matching_supports_verified_aliases_and_rejects_negated_skills(self) -> None:
        result = build_tailoring_result(
            "Backend engineer\nBuilt services with Postgres.",
            "PostgreSQL and Python",
        )

        self.assertEqual([item.value for item in result.matches], ["PostgreSQL"])
        self.assertIn("Resume line 2", result.matches[0].evidence or "")
        self.assertEqual([item.value for item in result.gaps], ["Python"])

        negated = build_tailoring_result("Developer\nNo Python experience.", "Python")
        self.assertEqual([item.value for item in negated.gaps], ["Python"])


if __name__ == "__main__":
    unittest.main()
