import unittest

from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from app.config import settings
from app.core.middleware import csrf_protection_middleware
from app.core.security import create_access_token, create_csrf_token


class AuthCsrfE2ESmokeTestCase(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.middleware('http')(csrf_protection_middleware)

        @app.post('/api/v1/auth/login')
        def login(response: Response):
            token = create_access_token({'sub': '1', 'role': 'ADMIN'})
            csrf = create_csrf_token(subject='1')
            response.set_cookie(settings.AUTH_COOKIE_NAME, token, httponly=True, path='/')
            response.set_cookie(settings.CSRF_COOKIE_NAME, csrf, httponly=False, path='/')
            return {'ok': True}

        @app.post('/api/v1/protected/mutate')
        def mutate():
            return {'ok': True}

        self.client = TestClient(app)

    def test_login_then_mutable_requires_csrf(self):
        login_resp = self.client.post('/api/v1/auth/login')
        self.assertEqual(login_resp.status_code, 200)

        auth_cookie = login_resp.cookies.get(settings.AUTH_COOKIE_NAME)
        csrf_cookie = login_resp.cookies.get(settings.CSRF_COOKIE_NAME)
        self.assertTrue(auth_cookie)
        self.assertTrue(csrf_cookie)

        self.client.cookies.set(settings.AUTH_COOKIE_NAME, auth_cookie)
        self.client.cookies.set(settings.CSRF_COOKIE_NAME, csrf_cookie)

        blocked = self.client.post(
            '/api/v1/protected/mutate',
            headers={'Origin': settings.cors_origins_list[0]},
        )
        self.assertEqual(blocked.status_code, 403)

        allowed = self.client.post(
            '/api/v1/protected/mutate',
            headers={
                'Origin': settings.cors_origins_list[0],
                settings.CSRF_HEADER_NAME: csrf_cookie,
            },
        )
        self.assertEqual(allowed.status_code, 200)


if __name__ == '__main__':
    unittest.main()
