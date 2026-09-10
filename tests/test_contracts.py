import unittest

from pydantic import ValidationError

from app.safety import parse_rewrite_output
from app.schemas import RewriteOutput, TailoringRequest


class ContractTests(unittest.TestCase):
    def test_rewrite_output_requires_strict_fields(self) -> None:
        output = parse_rewrite_output(
            '{"summary":"Python developer","experience":["Built APIs"],"skills":["Python"],"unsupported_claims":[]}'
        )

        self.assertIsInstance(output, RewriteOutput)
        self.assertEqual(output.skills, ["Python"])

    def test_malformed_rewrite_output_is_rejected_safely(self) -> None:
        with self.assertRaisesRegex(ValueError, "valid JSON"):
            parse_rewrite_output("not-json")
        with self.assertRaisesRegex(ValueError, "required schema"):
            parse_rewrite_output('{"summary":"missing other fields"}')

    def test_api_request_rejects_extra_fields(self) -> None:
        with self.assertRaises(ValidationError):
            TailoringRequest(resume="Resume", job_description="Job", secret="hidden")


if __name__ == "__main__":
    unittest.main()
