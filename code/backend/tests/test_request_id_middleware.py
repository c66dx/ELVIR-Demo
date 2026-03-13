import asyncio
import unittest

from starlette.requests import Request
from starlette.responses import Response

from app.core.middleware import request_id_middleware


class RequestIdMiddlewareTestCase(unittest.TestCase):
    def _build_request(self, headers=None):
        headers = headers or []
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/health",
            "raw_path": b"/health",
            "headers": headers,
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
            "root_path": "",
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        return Request(scope, receive)

    def test_reuses_incoming_request_id(self):
        req = self._build_request(headers=[(b"x-request-id", b"abc-123")])

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(request_id_middleware(req, call_next))

        self.assertEqual(response.headers.get("X-Request-ID"), "abc-123")
        self.assertEqual(req.state.request_id, "abc-123")

    def test_logs_and_reraises_when_call_next_fails(self):
        req = self._build_request(headers=[(b"x-request-id", b"req-fail")])

        async def call_next(_request):
            raise RuntimeError("boom")

        with self.assertLogs("elvir.api", level="ERROR") as logs:
            with self.assertRaises(RuntimeError):
                asyncio.run(request_id_middleware(req, call_next))

        self.assertEqual(req.state.request_id, "req-fail")
        joined = "\n".join(logs.output)
        self.assertIn("request_id=req-fail", joined)
        self.assertIn("status=500", joined)

    def test_generates_request_id_when_missing(self):
        req = self._build_request()

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(request_id_middleware(req, call_next))

        rid = response.headers.get("X-Request-ID")
        self.assertIsNotNone(rid)
        self.assertEqual(req.state.request_id, rid)
        self.assertEqual(len(rid), 32)


if __name__ == "__main__":
    unittest.main()
