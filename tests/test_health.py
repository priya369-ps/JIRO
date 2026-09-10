import unittest

from app.main import MISSION, PIPELINE_STAGES, health_check


class HealthCheckTests(unittest.TestCase):
    def test_health_check_exposes_mission_contract(self) -> None:
        response = health_check()

        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["service"], "JIRO")
        self.assertEqual(response["mission"], MISSION)
        self.assertEqual(response["pipeline"], list(PIPELINE_STAGES))
        self.assertEqual(response["fabrication_policy"], "never_invent_source_facts")
        self.assertEqual(response["configuration"]["product_decisions"]["frontend"], "fastapi_text_first_nextjs_future")


if __name__ == "__main__":
    unittest.main()
