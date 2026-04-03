import asyncio
import unittest
from unittest.mock import patch

from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.core.middleware import security_headers_middleware


class SecurityHeadersMiddlewareTestCase(unittest.TestCase):
    def _build_request(self):
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/health",
            "raw_path": b"/health",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
            "root_path": "",
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        return Request(scope, receive)

    def test_adds_default_hardening_headers(self):
        req = self._build_request()

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(security_headers_middleware(req, call_next))

        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(response.headers.get("Referrer-Policy"), "no-referrer")
        self.assertEqual(
            response.headers.get("Permissions-Policy"),
            "camera=(), geolocation=(), interest-cohort=()",
        )
        self.assertIn("default-src", response.headers.get("Content-Security-Policy", ""))
        self.assertIsNone(response.headers.get("Strict-Transport-Security"))

    def test_adds_hsts_in_production(self):
        req = self._build_request()

        async def call_next(_request):
            return Response(status_code=200)

        with patch.object(settings, "ENV", "prod"):
            response = asyncio.run(security_headers_middleware(req, call_next))

        self.assertEqual(
            response.headers.get("Strict-Transport-Security"),
            "max-age=31536000; includeSubDomains",
        )

    def test_does_not_override_existing_headers(self):
        req = self._build_request()

        async def call_next(_request):
            response = Response(status_code=200)
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            return response

        response = asyncio.run(security_headers_middleware(req, call_next))

        self.assertEqual(response.headers.get("X-Frame-Options"), "SAMEORIGIN")


if __name__ == "__main__":
    unittest.main()
