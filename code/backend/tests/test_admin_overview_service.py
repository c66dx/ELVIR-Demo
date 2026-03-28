"""Tests de build_users_overview (panel admin)."""
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.assignment import Assignment
from app.models.professional import Professional
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation
from app.services.admin_overview_service import build_users_overview


class AdminOverviewServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.u_prof = User(
            email="prof@test.cl",
            password_hash="x",
            role="PROFESIONAL",
            is_active=True,
            profile_photo_url="https://p.jpg",
        )
        self.u_y1 = User(
            email="j1@test.cl",
            password_hash="x",
            role="JOVEN",
            is_active=True,
        )
        self.u_y2 = User(
            email="j2@test.cl",
            password_hash="x",
            role="JOVEN",
            is_active=True,
        )
        self.db.add_all([self.u_prof, self.u_y1, self.u_y2])
        self.db.flush()

        self.prof = Professional(user_id=self.u_prof.id, display_name="Prof Uno", is_active=True)
        self.db.add(self.prof)
        self.db.flush()

        self.y_linked = Youth(
            user_id=self.u_y1.id,
            display_name="Joven Vinculado",
            identifier="JOV-001",
            login_enabled=True,
            is_active=True,
        )
        self.y_other = Youth(
            user_id=self.u_y2.id,
            display_name="Otro Nombre",
            identifier="JOV-002",
            login_enabled=True,
            is_active=True,
        )
        self.y_pending = Youth(
            user_id=None,
            display_name="Pendiente",
            identifier="JOV-P",
            login_enabled=False,
            is_active=True,
        )
        self.db.add_all([self.y_linked, self.y_other, self.y_pending])
        self.db.flush()

        self.db.add(
            Assignment(
                youth_id=self.y_linked.id,
                professional_id=self.prof.id,
                status="ACTIVO",
            )
        )
        self.db.add(
            YouthInvitation(
                youth_id=self.y_pending.id,
                email="pend@inv.cl",
                token="tok-pend-ov",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_full_overview_without_pagination(self):
        out = build_users_overview(self.db, tab=None, page=None, page_size=None, search=None)
        self.assertIsNone(out.meta)
        self.assertEqual(len(out.youths), 3)
        self.assertEqual(len(out.professionals), 1)
        linked = next(y for y in out.youths if y.identifier == "JOV-001")
        self.assertEqual(linked.email, "j1@test.cl")
        self.assertIsNotNone(linked.assigned_professional)
        self.assertEqual(linked.assigned_professional.display_name, "Prof Uno")
        pend = next(y for y in out.youths if y.identifier == "JOV-P")
        self.assertEqual(pend.email, "pend@inv.cl")

    def test_tab_youths_pagination(self):
        out = build_users_overview(self.db, tab="youths", page=1, page_size=2, search=None)
        self.assertIsNotNone(out.meta)
        self.assertIsNotNone(out.meta.youths)
        self.assertEqual(out.meta.youths.total, 3)
        self.assertEqual(len(out.youths), 2)
        self.assertEqual(len(out.professionals), 0)

    def test_tab_professionals_only(self):
        out = build_users_overview(self.db, tab="professionals", page=1, page_size=10, search=None)
        self.assertIsNotNone(out.meta.professionals)
        self.assertEqual(out.meta.professionals.total, 1)
        self.assertEqual(len(out.professionals), 1)
        self.assertEqual(len(out.youths), 0)

    def test_search_youths_by_display_name(self):
        out = build_users_overview(self.db, tab="youths", page=1, page_size=10, search="Otro")
        self.assertEqual(len(out.youths), 1)
        self.assertEqual(out.youths[0].identifier, "JOV-002")


if __name__ == "__main__":
    unittest.main()
