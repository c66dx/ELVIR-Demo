"""Clave de rate limit (IP / X-Forwarded-For)."""
import unittest

from starlette.requests import Request

from app.core.limiter import get_rate_limit_key


def _request(
    *,
    client: tuple[str, int] = ("203.0.113.10", 1234),
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    h = headers or []
    return Request(
        scope={
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/v1/x",
            "raw_path": b"/api/v1/x",
            "root_path": "",
            "query_string": b"",
            "headers": h,
            "client": client,
            "server": ("proxy.local", 80),
        }
    )


class GetRateLimitKeyTestCase(unittest.TestCase):
    def test_without_trust_uses_client_host(self):
        req = _request()
        key = get_rate_limit_key(req)
        self.assertEqual(key, "203.0.113.10")

    def test_with_trust_uses_first_forwarded_hop(self):
        req = _request(
            headers=[(b"x-forwarded-for", b"198.51.100.1, 10.0.0.1")],
        )
        from app.config import settings

        prev = settings.RATE_LIMIT_TRUST_X_FORWARDED_FOR
        try:
            object.__setattr__(settings, "RATE_LIMIT_TRUST_X_FORWARDED_FOR", True)
            key = get_rate_limit_key(req)
            self.assertEqual(key, "198.51.100.1")
        finally:
            object.__setattr__(settings, "RATE_LIMIT_TRUST_X_FORWARDED_FOR", prev)

    def test_with_trust_but_empty_forwarded_falls_back_to_client(self):
        req = _request()
        from app.config import settings

        prev = settings.RATE_LIMIT_TRUST_X_FORWARDED_FOR
        try:
            object.__setattr__(settings, "RATE_LIMIT_TRUST_X_FORWARDED_FOR", True)
            key = get_rate_limit_key(req)
            self.assertEqual(key, "203.0.113.10")
        finally:
            object.__setattr__(settings, "RATE_LIMIT_TRUST_X_FORWARDED_FOR", prev)


if __name__ == "__main__":
    unittest.main()
