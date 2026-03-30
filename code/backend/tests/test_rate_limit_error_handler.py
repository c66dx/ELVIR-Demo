"""Respuesta 429 alineada con ErrorResponse (handler propio)."""
import asyncio
import json
import unittest

from limits import parse
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.wrappers import Limit
from starlette.requests import Request

from app.core.errors import ErrorCode
from app.main import app, rate_limit_exceeded_handler


class RateLimitErrorHandlerTestCase(unittest.TestCase):
    def test_rate_limit_handler_returns_standard_error_shape(self):
        lim = Limit(
            parse("1/minute"),
            get_remote_address,
            None,
            False,
            None,
            None,
            None,
            1,
            True,
        )
        exc = RateLimitExceeded(lim)
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/auth/login",
            "raw_path": b"/api/v1/auth/login",
            "root_path": "",
            "query_string": b"",
            "headers": [(b"host", b"test.local")],
            "client": ("127.0.0.1", 1),
            "server": ("test.local", 80),
            "app": app,
        }
        request = Request(scope)
        request.state.request_id = "req-test-429"
        request.state.view_rate_limit = None

        out = asyncio.run(rate_limit_exceeded_handler(request, exc))
        self.assertEqual(out.status_code, 429)
        data = json.loads(out.body.decode())
        self.assertIn("Demasiadas solicitudes", data["detail"])
        self.assertEqual(data["error"]["code"], ErrorCode.RATE_LIMIT_EXCEEDED.value)
        self.assertEqual(data["error"]["request_id"], "req-test-429")
        self.assertIn("1 per 1 minute", data["detail"])


if __name__ == "__main__":
    unittest.main()
