"""Integración ligera: app real, TestClient, SQLite en memoria (vía conftest)."""
import unittest

from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from app.database import Base, SessionLocal, engine, get_db
from app.main import app
from app.models.professional import Professional
from app.models.user import User


def _override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ApiIntegrationSmokeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        app.dependency_overrides[get_db] = _override_get_db
        cls.client = TestClient(app)

        db = SessionLocal()
        try:
            u = User(
                email="integ@test.cl",
                password_hash=get_password_hash("secret123"),
                role="PROFESIONAL",
                is_active=True,
            )
            db.add(u)
            db.flush()
            db.add(Professional(user_id=u.id, display_name="Integ", is_active=True))
            db.commit()
        finally:
            db.close()

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)

    def test_health_ok(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("status"), "ok")

    def test_login_ok_returns_token(self):
        r = self.client.post(
            "/api/v1/auth/login",
            json={"email": "integ@test.cl", "password": "secret123"},
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("access_token", body)
        self.assertEqual(body.get("role"), "PROFESIONAL")


if __name__ == "__main__":
    unittest.main()
