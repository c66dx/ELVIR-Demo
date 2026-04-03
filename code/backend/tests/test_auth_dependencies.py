import unittest
from types import SimpleNamespace

from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.config import settings
from app.core.dependencies import _resolve_access_token


class AuthDependenciesTestCase(unittest.TestCase):
    def _build_request(self, cookie_header: str | None = None):
        headers = []
        if cookie_header:
            headers.append((b"cookie", cookie_header.encode("utf-8")))
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

    def test_prefers_bearer_token_over_cookie(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=cookie-token")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="header-token")

        token = _resolve_access_token(request, credentials)
        self.assertEqual(token, "header-token")

    def test_trims_bearer_token_whitespace(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=cookie-token")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="  header-token  ")

        token = _resolve_access_token(request, credentials)
        self.assertEqual(token, "header-token")

    def test_empty_bearer_token_falls_back_to_cookie(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=cookie-token")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="   ")

        token = _resolve_access_token(request, credentials)
        self.assertEqual(token, "cookie-token")

    def test_rejects_bearer_token_with_inner_whitespace(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=cookie-token")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="abc def")

        token = _resolve_access_token(request, credentials)
        self.assertEqual(token, "cookie-token")

    def test_rejects_overlong_bearer_token_and_falls_back_to_cookie(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=cookie-token")
        overlong = "a" * 4097
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=overlong)

        token = _resolve_access_token(request, credentials)
        self.assertEqual(token, "cookie-token")

    def test_reads_cookie_when_header_missing(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=cookie-token")

        token = _resolve_access_token(request, None)
        self.assertEqual(token, "cookie-token")

    def test_trims_cookie_token_whitespace(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=  cookie-token  ")

        token = _resolve_access_token(request, None)
        self.assertEqual(token, "cookie-token")

    def test_rejects_cookie_token_with_inner_whitespace(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=abc def")

        token = _resolve_access_token(request, None)
        self.assertIsNone(token)

    def test_rejects_overlong_cookie_token(self):
        overlong = "a" * 4097
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}={overlong}")

        token = _resolve_access_token(request, None)
        self.assertIsNone(token)

    def test_blank_cookie_token_returns_none(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=   ")

        token = _resolve_access_token(request, None)
        self.assertIsNone(token)

    def test_handles_bearer_scheme_with_whitespace(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=cookie-token")
        credentials = SimpleNamespace(scheme="  Bearer  ", credentials="header-token")

        token = _resolve_access_token(request, credentials)
        self.assertEqual(token, "header-token")

    def test_ignores_non_bearer_scheme_and_falls_back_to_cookie(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=cookie-token")
        credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="header-token")

        token = _resolve_access_token(request, credentials)
        self.assertEqual(token, "cookie-token")

    def test_ignores_non_bearer_scheme_without_cookie(self):
        request = self._build_request()
        credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="header-token")

        token = _resolve_access_token(request, credentials)
        self.assertIsNone(token)

    def test_handles_missing_scheme_in_credentials_object(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=cookie-token")
        credentials = SimpleNamespace(scheme=None, credentials="header-token")

        token = _resolve_access_token(request, credentials)
        self.assertEqual(token, "cookie-token")

    def test_handles_missing_credentials_in_credentials_object(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=cookie-token")
        credentials = SimpleNamespace(scheme="Bearer")

        token = _resolve_access_token(request, credentials)
        self.assertEqual(token, "cookie-token")

    def test_handles_non_string_scheme_in_credentials_object(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=cookie-token")
        credentials = SimpleNamespace(scheme=123, credentials="header-token")

        token = _resolve_access_token(request, credentials)
        self.assertEqual(token, "cookie-token")

    def test_ignores_non_string_bearer_credentials_and_falls_back_to_cookie(self):
        request = self._build_request(cookie_header=f"{settings.AUTH_COOKIE_NAME}=cookie-token")
        credentials = SimpleNamespace(scheme="Bearer", credentials=12345)

        token = _resolve_access_token(request, credentials)
        self.assertEqual(token, "cookie-token")

    def test_returns_none_when_no_auth(self):
        request = self._build_request()

        token = _resolve_access_token(request, None)
        self.assertIsNone(token)


if __name__ == "__main__":
    unittest.main()
