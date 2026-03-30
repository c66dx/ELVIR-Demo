import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from app.database import Base
from app.models.assignment import Assignment
from app.models.professional import Professional
from app.models.user import User
from app.models.youth import Youth
from app.routers.admin import admin_delete_professional, admin_delete_youth


def _admin_router_request() -> Request:
    """Request ASGI mínimo (slowapi exige starlette.requests.Request)."""
    return Request(
        scope={
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "DELETE",
            "scheme": "http",
            "path": "/api/v1/admin",
            "raw_path": b"/api/v1/admin",
            "root_path": "",
            "query_string": b"",
            "headers": [(b"host", b"test.local")],
            "client": ("127.0.0.1", 12345),
            "server": ("test.local", 80),
        }
    )


class AdminRouterTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.admin_user = User(email="admin@test.cl", password_hash="x", role="ADMIN", is_active=True)
        self.prof_user = User(email="prof@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.youth_user = User(email="joven@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add_all([self.admin_user, self.prof_user, self.youth_user])
        self.db.flush()

        self.prof = Professional(user_id=self.prof_user.id, display_name="Pro 1", is_active=True)
        self.db.add(self.prof)
        self.db.flush()

        self.youth = Youth(
            user_id=self.youth_user.id,
            display_name="Joven",
            identifier="JOV-001",
            login_enabled=True,
            is_active=True,
        )
        self.db.add(self.youth)
        self.db.flush()

        self.assignment = Assignment(youth_id=self.youth.id, professional_id=self.prof.id, status="ACTIVO")
        self.db.add(self.assignment)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_admin_delete_youth_disables_login_and_assignments(self):
        result = admin_delete_youth(
            _admin_router_request(), self.youth.id, admin=self.admin_user, db=self.db
        )
        self.assertTrue(result.get("ok"))

        self.db.refresh(self.youth)
        self.assertFalse(self.youth.is_active)
        self.assertFalse(self.youth.login_enabled)

        self.db.refresh(self.youth_user)
        self.assertFalse(self.youth_user.is_active)
        self.assertTrue(self.youth_user.email.startswith(f"disabled+{self.youth_user.id}@"))

        assignment = self.db.query(Assignment).filter(Assignment.id == self.assignment.id).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.status, "INACTIVO")
        self.assertIsNotNone(assignment.ended_at)

    def test_admin_delete_professional_disables_user_and_assignments(self):
        result = admin_delete_professional(
            _admin_router_request(), self.prof.id, admin=self.admin_user, db=self.db
        )
        self.assertTrue(result.get("ok"))

        self.db.refresh(self.prof)
        self.assertFalse(self.prof.is_active)

        self.db.refresh(self.prof_user)
        self.assertFalse(self.prof_user.is_active)
        self.assertTrue(self.prof_user.email.startswith(f"disabled+{self.prof_user.id}@"))

        assignment = self.db.query(Assignment).filter(Assignment.id == self.assignment.id).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.status, "INACTIVO")
        self.assertIsNotNone(assignment.ended_at)


if __name__ == "__main__":
    unittest.main()
