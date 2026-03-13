import asyncio
import unittest

from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.core.middleware import csrf_protection_middleware
from app.core.security import create_access_token, create_csrf_token


class CsrfMiddlewareTestCase(unittest.TestCase):
    def _auth_cookies(self, user_id: str = "1") -> tuple[str, str]:
        access = create_access_token({"sub": user_id, "role": "PROFESIONAL"})
        csrf = create_csrf_token(subject=user_id)
        return access, csrf

    def _build_request(self, method: str, headers=None, path: str = "/api/v1/youths"):
        headers = headers or []
        raw_path = path.encode("utf-8")
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "path": path,
            "raw_path": raw_path,
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

    def test_allows_get_without_csrf(self):
        req = self._build_request("GET")

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 200)


    def test_allows_mutable_without_auth_cookie(self):
        req = self._build_request("POST")

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 200)

    def test_allows_exempt_auth_login_path_even_with_auth_cookie(self):
        access, _ = self._auth_cookies()
        cookie = f"{settings.AUTH_COOKIE_NAME}={access}"
        scope_headers = [(b"cookie", cookie.encode("utf-8"))]
        req = self._build_request("POST", headers=scope_headers, path="/api/v1/auth/login")

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 200)

    def test_blocks_mutable_with_auth_cookie_and_missing_csrf(self):
        access, _ = self._auth_cookies()
        cookie = f"{settings.AUTH_COOKIE_NAME}={access}"
        req = self._build_request("POST", headers=[(b"cookie", cookie.encode("utf-8"))])

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 403)


    def test_blank_auth_cookie_does_not_trigger_csrf_checks(self):
        req = self._build_request(
            "POST",
            headers=[(b"cookie", f"{settings.AUTH_COOKIE_NAME}=   ".encode("utf-8"))],
        )

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 200)

    def test_allows_csrf_tokens_with_surrounding_whitespace(self):
        access, csrf = self._auth_cookies()
        cookie = f"{settings.AUTH_COOKIE_NAME}={access}; {settings.CSRF_COOKIE_NAME}=  {csrf}  "
        allowed_origin = settings.cors_origins_list[0].encode("utf-8")
        req = self._build_request(
            "POST",
            headers=[
                (b"cookie", cookie.encode("utf-8")),
                (b"origin", allowed_origin),
                (settings.CSRF_HEADER_NAME.lower().encode("utf-8"), f"  {csrf}  ".encode("utf-8")),
            ],
        )

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 200)

    def test_allows_blank_origin_header_when_referer_is_allowed(self):
        access, csrf = self._auth_cookies()
        cookie = f"{settings.AUTH_COOKIE_NAME}={access}; {settings.CSRF_COOKIE_NAME}={csrf}"
        allowed_referer = (settings.cors_origins_list[0] + '/alguna/ruta').encode('utf-8')
        req = self._build_request(
            "POST",
            headers=[
                (b"cookie", cookie.encode("utf-8")),
                (b"origin", b"   "),
                (b"referer", allowed_referer),
                (settings.CSRF_HEADER_NAME.lower().encode("utf-8"), csrf.encode("utf-8")),
            ],
        )

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 200)

    def test_blocks_when_csrf_cookie_and_header_do_not_match(self):
        access, csrf = self._auth_cookies()
        cookie = f"{settings.AUTH_COOKIE_NAME}={access}; {settings.CSRF_COOKIE_NAME}={csrf}"
        allowed_origin = settings.cors_origins_list[0].encode("utf-8")
        req = self._build_request(
            "POST",
            headers=[
                (b"cookie", cookie.encode("utf-8")),
                (b"origin", allowed_origin),
                (settings.CSRF_HEADER_NAME.lower().encode("utf-8"), (csrf + "x").encode("utf-8")),
            ],
        )

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 403)

    def test_blocks_mutable_with_disallowed_origin(self):
        access, csrf = self._auth_cookies()
        cookie = f"{settings.AUTH_COOKIE_NAME}={access}; {settings.CSRF_COOKIE_NAME}={csrf}"
        req = self._build_request(
            "POST",
            headers=[
                (b"cookie", cookie.encode("utf-8")),
                (b"origin", b"https://evil.example"),
                (settings.CSRF_HEADER_NAME.lower().encode("utf-8"), csrf.encode("utf-8")),
            ],
        )

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 403)


    def test_blocks_mutable_with_auth_cookie_without_origin_or_referer(self):
        access, csrf = self._auth_cookies()
        cookie = f"{settings.AUTH_COOKIE_NAME}={access}; {settings.CSRF_COOKIE_NAME}={csrf}"
        req = self._build_request(
            "POST",
            headers=[
                (b"cookie", cookie.encode("utf-8")),
                (settings.CSRF_HEADER_NAME.lower().encode("utf-8"), csrf.encode("utf-8")),
            ],
        )

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 403)

    def test_allows_mutable_with_allowed_referer_and_valid_csrf(self):
        access, csrf = self._auth_cookies()
        cookie = f"{settings.AUTH_COOKIE_NAME}={access}; {settings.CSRF_COOKIE_NAME}={csrf}"
        allowed_referer = (settings.cors_origins_list[0] + '/alguna/ruta').encode('utf-8')
        req = self._build_request(
            "POST",
            headers=[
                (b"cookie", cookie.encode("utf-8")),
                (b"referer", allowed_referer),
                (settings.CSRF_HEADER_NAME.lower().encode("utf-8"), csrf.encode("utf-8")),
            ],
        )

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 200)


    def test_allows_origin_with_trailing_slash_when_base_origin_is_allowed(self):
        access, csrf = self._auth_cookies()
        cookie = f"{settings.AUTH_COOKIE_NAME}={access}; {settings.CSRF_COOKIE_NAME}={csrf}"
        origin_with_slash = (settings.cors_origins_list[0] + '/').encode('utf-8')
        req = self._build_request(
            "POST",
            headers=[
                (b"cookie", cookie.encode("utf-8")),
                (b"origin", origin_with_slash),
                (settings.CSRF_HEADER_NAME.lower().encode("utf-8"), csrf.encode("utf-8")),
            ],
        )

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 200)

    def test_blocks_malformed_origin_even_with_valid_csrf_token(self):
        access, csrf = self._auth_cookies()
        cookie = f"{settings.AUTH_COOKIE_NAME}={access}; {settings.CSRF_COOKIE_NAME}={csrf}"
        req = self._build_request(
            "POST",
            headers=[
                (b"cookie", cookie.encode("utf-8")),
                (b"origin", b"not-a-valid-origin"),
                (settings.CSRF_HEADER_NAME.lower().encode("utf-8"), csrf.encode("utf-8")),
            ],
        )

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 403)


    def test_blocks_when_csrf_subject_does_not_match_auth_subject(self):
        access, _ = self._auth_cookies(user_id="1")
        _, csrf_other = self._auth_cookies(user_id="2")
        cookie = f"{settings.AUTH_COOKIE_NAME}={access}; {settings.CSRF_COOKIE_NAME}={csrf_other}"
        allowed_origin = settings.cors_origins_list[0].encode("utf-8")
        req = self._build_request(
            "POST",
            headers=[
                (b"cookie", cookie.encode("utf-8")),
                (b"origin", allowed_origin),
                (settings.CSRF_HEADER_NAME.lower().encode("utf-8"), csrf_other.encode("utf-8")),
            ],
        )

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 403)

    def test_allows_mutable_with_uppercase_origin_and_valid_csrf(self):
        access, csrf = self._auth_cookies()
        cookie = f"{settings.AUTH_COOKIE_NAME}={access}; {settings.CSRF_COOKIE_NAME}={csrf}"
        allowed_origin_upper = settings.cors_origins_list[0].upper().encode("utf-8")
        req = self._build_request(
            "POST",
            headers=[
                (b"cookie", cookie.encode("utf-8")),
                (b"origin", allowed_origin_upper),
                (settings.CSRF_HEADER_NAME.lower().encode("utf-8"), csrf.encode("utf-8")),
            ],
        )

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 200)

    def test_allows_mutable_with_allowed_origin_and_valid_csrf(self):
        access, csrf = self._auth_cookies()
        cookie = f"{settings.AUTH_COOKIE_NAME}={access}; {settings.CSRF_COOKIE_NAME}={csrf}"
        allowed_origin = settings.cors_origins_list[0].encode("utf-8")
        req = self._build_request(
            "POST",
            headers=[
                (b"cookie", cookie.encode("utf-8")),
                (b"origin", allowed_origin),
                (settings.CSRF_HEADER_NAME.lower().encode("utf-8"), csrf.encode("utf-8")),
            ],
        )

        async def call_next(_request):
            return Response(status_code=200)

        response = asyncio.run(csrf_protection_middleware(req, call_next))
        self.assertEqual(response.status_code, 200)



if __name__ == "__main__":
    unittest.main()
