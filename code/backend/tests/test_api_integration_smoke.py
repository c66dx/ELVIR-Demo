"""Integración ligera: app real, TestClient, misma BD que `DATABASE_URL` (localmente SQLite en memoria).

En CI con PostgreSQL (`backend-tests-postgres`) valida también contra el motor de producción.
Cubre flujos críticos: salud, login, /me, denegación de rol admin y creación de sesión AUTOGESTIONADA.
"""
import unittest

from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from app.database import Base, SessionLocal, engine, get_db
from app.main import app
from app.models.case import Case
from app.models.job_role import JobRole
from app.models.professional import Professional
from app.models.simulation_template import SimulationTemplate
from app.models.user import User
from app.models.youth import Youth


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

            u_joven = User(
                email="joven-integ@test.cl",
                password_hash=get_password_hash("secret123"),
                role="JOVEN",
                is_active=True,
            )
            db.add(u_joven)
            db.flush()
            y = Youth(
                user_id=u_joven.id,
                display_name="Joven Integ",
                identifier="JOV-INT-1",
                login_enabled=True,
                is_active=True,
            )
            db.add(y)
            db.flush()

            job_role = JobRole(
                slug="integ-rol",
                name="Rol Integ",
                description="Desc",
                objetivo="Obj",
                competencias="[]",
                is_active=True,
            )
            case = Case(
                slug="integ-case",
                name="Caso Integ",
                difficulty="NORMAL",
                prompt_instructions="Instr",
                is_active=True,
            )
            db.add_all([job_role, case])
            db.flush()
            tpl = SimulationTemplate(
                job_role_id=job_role.id,
                case_id=case.id,
                liveavatar_context_id="ctx-integ",
                liveavatar_avatar_id="avatar-integ",
                liveavatar_voice_id="voice-integ",
                is_active=True,
            )
            db.add(tpl)
            db.commit()

            cls._youth_id = y.id
            cls._template_id = tpl.id
        finally:
            db.close()

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)

    def test_health_ok(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body.get("status"), "ok")
        self.assertEqual(body.get("service"), "elvir-api")
        self.assertEqual(body.get("version"), app.version)

    def test_health_live_ok(self):
        r = self.client.get("/health/live")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("checks", {}).get("process"), "ok")

    def test_health_ready_database_ok(self):
        r = self.client.get("/health/ready")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("checks", {}).get("database"), "ok")

    def test_login_ok_returns_token(self):
        r = self.client.post(
            "/api/v1/auth/login",
            json={"email": "integ@test.cl", "password": "secret123"},
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("access_token", body)
        self.assertEqual(body.get("role"), "PROFESIONAL")

    def test_login_wrong_password_401(self):
        r = self.client.post(
            "/api/v1/auth/login",
            json={"email": "integ@test.cl", "password": "mala"},
        )
        self.assertEqual(r.status_code, 401)
        body = r.json()
        self.assertIn("detail", body)

    def test_me_with_bearer_returns_user(self):
        login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "integ@test.cl", "password": "secret123"},
        )
        token = login.json()["access_token"]
        r = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(r.status_code, 200)
        me = r.json()
        self.assertEqual(me.get("role"), "PROFESIONAL")
        self.assertEqual(me.get("email"), "integ@test.cl")
        self.assertIsNotNone(me.get("professional_id"))

    def test_professional_cannot_access_admin_overview(self):
        login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "integ@test.cl", "password": "secret123"},
        )
        token = login.json()["access_token"]
        r = self.client.get(
            "/api/v1/admin/users/overview",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(r.status_code, 403)

    def test_youth_create_autogestionada_session(self):
        login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "joven-integ@test.cl", "password": "secret123"},
        )
        self.assertEqual(login.status_code, 200)
        token = login.json()["access_token"]
        # Sin cookies de sesión el middleware CSRF no exige cabecera (solo Bearer); el TestClient conserva cookies del login.
        self.client.cookies.clear()
        r = self.client.post(
            "/api/v1/sessions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "youth_id": self._youth_id,
                "simulation_template_id": self._template_id,
                "mode": "AUTOGESTIONADA",
            },
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body.get("youth_id"), self._youth_id)
        self.assertEqual(body.get("mode"), "AUTOGESTIONADA")
        self.assertEqual(body.get("status"), "EN_CURSO")
        self.assertIsNone(body.get("professional_id"))


if __name__ == "__main__":
    unittest.main()
