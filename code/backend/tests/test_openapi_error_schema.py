import unittest

from fastapi.testclient import TestClient

from app.core.errors import ErrorCode
from app.main import app


class OpenApiErrorSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_openapi_includes_error_response_schema(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        components = payload.get("components", {})
        schemas = components.get("schemas", {})
        responses = components.get("responses", {})
        headers = components.get("headers", {})

        self.assertIn("ErrorResponse", schemas)
        self.assertIn("ErrorDetail", schemas)
        self.assertIn("ErrorResponse", responses)
        self.assertIn("X-Request-ID", headers)
        self.assertIn("X-Request-ID", responses["ErrorResponse"].get("headers", {}))
        description = responses["ErrorResponse"].get("description", "")
        for code in ErrorCode:
            self.assertIn(code.value, description)

        for path in ("/health", "/health/metrics", "/health/live", "/health/ready"):
            op = payload.get("paths", {}).get(path, {}).get("get", {})
            self.assertIn("health", op.get("tags", []), msg=f"path {path} should be tagged health")

        ready_responses = payload.get("paths", {}).get("/health/ready", {}).get("get", {}).get("responses", {})
        self.assertIn("503", ready_responses, msg="/health/ready should document 503 readiness failure")

        health_get = payload.get("paths", {}).get("/health", {}).get("get", {})
        responses = health_get.get("responses", {})
        self.assertIn("500", responses)
        self.assertEqual(responses["500"].get("$ref"), "#/components/responses/ErrorResponse")

        rl = components["responses"]["RateLimitExceeded"]
        self.assertEqual(
            rl["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/ErrorResponse",
        )
        self.assertIn("X-Request-ID", rl.get("headers", {}))


if __name__ == "__main__":
    unittest.main()
