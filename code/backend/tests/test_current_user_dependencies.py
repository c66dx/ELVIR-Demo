import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from app.core.dependencies import get_current_user, get_current_user_id
from app.database import Base
from app.models.user import User


class CurrentUserDependenciesTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()
        self.user = User(email="admin@test.cl", password_hash="x", role="ADMIN", is_active=True)
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def _build_request(self):
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/api/v1/auth/me",
            "raw_path": b"/api/v1/auth/me",
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

    def test_get_current_user_id_returns_none_when_sub_is_not_int(self):
        request = self._build_request()
        with patch("app.core.dependencies._resolve_access_token", return_value="token"), patch(
            "app.core.dependencies.decode_token", return_value={"sub": "abc"}
        ):
            user_id = get_current_user_id(request=request, credentials=None, db=self.db)

        self.assertIsNone(user_id)

    def test_get_current_user_id_returns_none_when_no_token(self):
        request = self._build_request()
        with patch("app.core.dependencies._resolve_access_token", return_value=None):
            user_id = get_current_user_id(request=request, credentials=None, db=self.db)

        self.assertIsNone(user_id)

    def test_get_current_user_raises_401_when_no_token(self):
        request = self._build_request()
        with patch("app.core.dependencies._resolve_access_token", return_value=None):
            with self.assertRaises(HTTPException) as ctx:
                get_current_user(request=request, credentials=None, db=self.db)

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail, "No autenticado")

    def test_get_current_user_raises_401_when_sub_is_not_int(self):
        request = self._build_request()
        with patch("app.core.dependencies._resolve_access_token", return_value="token"), patch(
            "app.core.dependencies.decode_token", return_value={"sub": "abc"}
        ):
            with self.assertRaises(HTTPException) as ctx:
                get_current_user(request=request, credentials=None, db=self.db)

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail, "Token inválido")

    def test_get_current_user_raises_401_when_user_not_found(self):
        request = self._build_request()
        with patch("app.core.dependencies._resolve_access_token", return_value="token"), patch(
            "app.core.dependencies.decode_token", return_value={"sub": "999"}
        ):
            with self.assertRaises(HTTPException) as ctx:
                get_current_user(request=request, credentials=None, db=self.db)

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail, "Usuario no encontrado")


if __name__ == "__main__":
    unittest.main()
