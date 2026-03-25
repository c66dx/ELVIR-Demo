import unittest

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.errors import ErrorCode, localize_email_validation_errors
from app.core.middleware import csrf_protection_middleware, request_id_middleware
from app.core.security import create_access_token, create_csrf_token
from app.main import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)


class Payload(BaseModel):
    count: int


class ErrorResponsesTestCase(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.middleware("http")(request_id_middleware)
        app.middleware("http")(csrf_protection_middleware)
        app.add_exception_handler(StarletteHTTPException, http_exception_handler)
        app.add_exception_handler(RequestValidationError, validation_exception_handler)
        app.add_exception_handler(Exception, unhandled_exception_handler)

        @app.post("/validate")
        def validate(payload: Payload):
            return {"count": payload.count}

        @app.post("/api/v1/protected/mutate")
        def mutate():
            return {"ok": True}

        @app.get("/http-error")
        def http_error():
            raise HTTPException(status_code=404, detail="Nope")

        self.client = TestClient(app)

    def _set_auth_cookies(self) -> str:
        access = create_access_token({"sub": "1", "role": "ADMIN"})
        csrf = create_csrf_token(subject="1")
        self.client.cookies.set(settings.AUTH_COOKIE_NAME, access)
        self.client.cookies.set(settings.CSRF_COOKIE_NAME, csrf)
        return csrf

    def test_csrf_error_payload_contains_error_and_request_id(self):
        self._set_auth_cookies()

        response = self.client.post(
            "/api/v1/protected/mutate",
            headers={"Origin": settings.cors_origins_list[0]},
        )
        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertEqual(body["detail"], "CSRF token inválido o ausente")
        self.assertEqual(body["error"]["message"], "CSRF token inválido o ausente")
        self.assertEqual(body["error"]["code"], ErrorCode.CSRF_FORBIDDEN.value)
        request_id = response.headers.get("X-Request-ID")
        self.assertTrue(request_id)
        self.assertEqual(body["error"]["request_id"], request_id)

    def test_validation_error_payload_contains_error_and_request_id(self):
        response = self.client.post("/validate", json={"count": "x"})
        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertIsInstance(body["detail"], list)
        self.assertEqual(body["error"]["message"], "Request error")
        self.assertEqual(body["error"]["code"], ErrorCode.VALIDATION_ERROR.value)
        request_id = response.headers.get("X-Request-ID")
        self.assertTrue(request_id)
        self.assertEqual(body["error"]["request_id"], request_id)

    def test_http_error_payload_contains_error_and_request_id(self):
        response = self.client.get("/http-error")
        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(body["detail"], "Nope")
        self.assertEqual(body["error"]["message"], "Nope")
        self.assertEqual(body["error"]["code"], ErrorCode.HTTP_ERROR.value)
        request_id = response.headers.get("X-Request-ID")
        self.assertTrue(request_id)
        self.assertEqual(body["error"]["request_id"], request_id)


class LocalizeEmailValidationErrorsTestCase(unittest.TestCase):
    def test_invalid_email_message_spanish(self):
        raw = [
            {
                "type": "value_error",
                "loc": ("body", "email"),
                "msg": "value is not a valid email address: not an email",
                "input": "x",
            }
        ]
        out = localize_email_validation_errors(raw)
        self.assertEqual(out[0]["msg"], "Introduce un correo electrónico válido.")

    def test_missing_email_spanish(self):
        raw = [{"type": "missing", "loc": ("body", "email"), "msg": "Field required"}]
        out = localize_email_validation_errors(raw)
        self.assertEqual(out[0]["msg"], "El correo es obligatorio.")

    def test_other_field_unchanged(self):
        raw = [{"type": "missing", "loc": ("body", "password"), "msg": "Field required"}]
        out = localize_email_validation_errors(raw)
        self.assertEqual(out[0]["msg"], "Field required")


if __name__ == "__main__":
    unittest.main()
