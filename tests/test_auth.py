import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import AuthenticationMiddleware


class AuthenticationTests(unittest.TestCase):
    def _build_app(self) -> FastAPI:
        protected = FastAPI()
        protected.add_middleware(AuthenticationMiddleware, token="test-token")

        @protected.get("/health")
        def health():
            return {"status": "ok"}

        @protected.get("/tailor")
        def tailor():
            return {"status": "protected"}

        return protected

    def test_health_is_public_and_api_requires_bearer_token(self) -> None:
        with TestClient(self._build_app()) as client:
            public_response = client.get("/health")
            unauthorized = client.get("/tailor")
            authorized = client.get("/tailor", headers={"Authorization": "Bearer test-token"})

        self.assertEqual(public_response.status_code, 200)
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        self.assertNotIn("test-token", unauthorized.text)

    def test_wrong_token_is_rejected(self) -> None:
        with TestClient(self._build_app()) as client:
            response = client.get("/tailor", headers={"Authorization": "Bearer wrong"})

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
