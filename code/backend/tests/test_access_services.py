"""Tests unitarios de reglas de acceso en servicios (sin pasar por el router HTTP)."""
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.assignment import Assignment
from app.models.professional import Professional
from app.models.user import User
from app.models.youth import Youth
from app.services.professional_access import (
    assert_can_access_professional,
    can_access_professional,
)
from app.services.youth_access import load_youth_or_404, require_youth_assigned_to_professional


class ProfessionalAccessServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.admin = User(email="a@test.cl", password_hash="x", role="ADMIN", is_active=True)
        self.prof_user = User(email="p@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.other_prof_user = User(email="p2@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.youth_user = User(email="j@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add_all([self.admin, self.prof_user, self.other_prof_user, self.youth_user])
        self.db.flush()

        self.prof = Professional(user_id=self.prof_user.id, display_name="P1", is_active=True)
        self.other_prof = Professional(user_id=self.other_prof_user.id, display_name="P2", is_active=True)
        self.db.add_all([self.prof, self.other_prof])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_admin_can_access_any_professional(self):
        self.assertTrue(can_access_professional(self.admin, self.prof.id, self.db))
        self.assertTrue(can_access_professional(self.admin, self.other_prof.id, self.db))

    def test_professional_only_own_profile(self):
        self.assertTrue(can_access_professional(self.prof_user, self.prof.id, self.db))
        self.assertFalse(can_access_professional(self.prof_user, self.other_prof.id, self.db))

    def test_youth_cannot_access_professional_resource(self):
        self.assertFalse(can_access_professional(self.youth_user, self.prof.id, self.db))

    def test_assert_raises_403_when_denied(self):
        with self.assertRaises(HTTPException) as ctx:
            assert_can_access_professional(self.prof_user, self.other_prof.id, self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_assert_ok_when_allowed(self):
        assert_can_access_professional(self.prof_user, self.prof.id, self.db)


class YouthAccessServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.prof_user = User(email="p@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.db.add(self.prof_user)
        self.db.flush()
        self.prof = Professional(user_id=self.prof_user.id, display_name="P1", is_active=True)
        self.db.add(self.prof)
        self.db.flush()

        self.youth = Youth(
            user_id=None,
            display_name="Y",
            identifier="JOV-001",
            login_enabled=False,
            is_active=True,
        )
        self.db.add(self.youth)
        self.db.flush()

        self.db.add(
            Assignment(
                youth_id=self.youth.id,
                professional_id=self.prof.id,
                status="ACTIVO",
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_load_youth_or_404_missing(self):
        with self.assertRaises(HTTPException) as ctx:
            load_youth_or_404(self.db, 99999)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_require_assigned_returns_youth(self):
        y = require_youth_assigned_to_professional(self.db, self.youth.id, self.prof)
        self.assertEqual(y.id, self.youth.id)

    def test_require_assigned_raises_without_assignment(self):
        u = User(email="p3@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.db.add(u)
        self.db.flush()
        other = Professional(user_id=u.id, display_name="Otro", is_active=True)
        self.db.add(other)
        self.db.commit()
        self.db.refresh(other)
        with self.assertRaises(HTTPException) as ctx:
            require_youth_assigned_to_professional(self.db, self.youth.id, other)
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
