"""Tests unitarios de assignment_service y require_session_access (servicios, sin router)."""
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.assignment import Assignment
from app.models.case import Case
from app.models.job_role import JobRole
from app.models.professional import Professional
from app.models.session import Session as SessionModel
from app.models.simulation_template import SimulationTemplate
from app.models.user import User
from app.models.youth import Youth
from app.services.assignment_service import (
    assert_user_can_create_assignment,
    assert_user_can_end_assignment,
)
from app.services.session_access import (
    require_session_access,
    require_session_for_start,
    touch_session_heartbeat,
)


class AssignmentServicePermissionsTestCase(unittest.TestCase):
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

    def test_create_assignment_admin_allowed(self):
        assert_user_can_create_assignment(self.db, self.admin, self.prof.id)

    def test_create_assignment_professional_self_allowed(self):
        assert_user_can_create_assignment(self.db, self.prof_user, self.prof.id)

    def test_create_assignment_professional_other_forbidden(self):
        with self.assertRaises(HTTPException) as ctx:
            assert_user_can_create_assignment(self.db, self.prof_user, self.other_prof.id)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_create_assignment_youth_forbidden(self):
        with self.assertRaises(HTTPException) as ctx:
            assert_user_can_create_assignment(self.db, self.youth_user, self.prof.id)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_end_assignment_admin_allowed(self):
        a = Assignment(youth_id=1, professional_id=self.prof.id, status="ACTIVO")
        self.db.add(a)
        self.db.commit()
        self.db.refresh(a)
        assert_user_can_end_assignment(self.db, self.admin, a)

    def test_end_assignment_owner_professional_allowed(self):
        a = Assignment(youth_id=1, professional_id=self.prof.id, status="ACTIVO")
        self.db.add(a)
        self.db.commit()
        self.db.refresh(a)
        assert_user_can_end_assignment(self.db, self.prof_user, a)

    def test_end_assignment_other_professional_forbidden(self):
        a = Assignment(youth_id=1, professional_id=self.prof.id, status="ACTIVO")
        self.db.add(a)
        self.db.commit()
        self.db.refresh(a)
        with self.assertRaises(HTTPException) as ctx:
            assert_user_can_end_assignment(self.db, self.other_prof_user, a)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_end_assignment_youth_forbidden(self):
        a = Assignment(youth_id=1, professional_id=self.prof.id, status="ACTIVO")
        self.db.add(a)
        self.db.commit()
        self.db.refresh(a)
        with self.assertRaises(HTTPException) as ctx:
            assert_user_can_end_assignment(self.db, self.youth_user, a)
        self.assertEqual(ctx.exception.status_code, 403)


class SessionAccessServiceTestCase(unittest.TestCase):
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
        self.youth_user = User(email="j@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.other_youth_user = User(email="j2@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add_all([self.prof_user, self.youth_user, self.other_youth_user])
        self.db.flush()

        self.prof = Professional(user_id=self.prof_user.id, display_name="P1", is_active=True)
        self.db.add(self.prof)
        self.db.flush()

        self.youth = Youth(
            user_id=self.youth_user.id,
            display_name="J1",
            identifier="JOV-001",
            login_enabled=True,
            is_active=True,
        )
        self.other_youth = Youth(
            user_id=self.other_youth_user.id,
            display_name="J2",
            identifier="JOV-002",
            login_enabled=True,
            is_active=True,
        )
        self.db.add_all([self.youth, self.other_youth])
        self.db.flush()

        self.db.add(
            Assignment(youth_id=self.youth.id, professional_id=self.prof.id, status="ACTIVO")
        )

        self.job_role = JobRole(
            slug="jr",
            name="JR",
            description="d",
            objetivo="o",
            competencias="[]",
            is_active=True,
        )
        self.case = Case(
            slug="c",
            name="C",
            difficulty="NORMAL",
            prompt_instructions="i",
            is_active=True,
        )
        self.db.add_all([self.job_role, self.case])
        self.db.flush()

        self.template = SimulationTemplate(
            job_role_id=self.job_role.id,
            case_id=self.case.id,
            liveavatar_context_id="ctx",
            liveavatar_avatar_id="av",
            liveavatar_voice_id="vo",
            is_active=True,
        )
        self.db.add(self.template)
        self.db.flush()

        self.sim_session = SessionModel(
            youth_id=self.youth.id,
            professional_id=self.prof.id,
            simulation_template_id=self.template.id,
            mode="SUPERVISADA",
            status="EN_CURSO",
        )
        self.db.add(self.sim_session)
        self.db.commit()
        self.db.refresh(self.sim_session)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_require_session_access_youth_own(self):
        s = require_session_access(self.db, self.sim_session.id, self.youth_user)
        self.assertEqual(s.id, self.sim_session.id)

    def test_require_session_access_youth_other_forbidden(self):
        with self.assertRaises(HTTPException) as ctx:
            require_session_access(self.db, self.sim_session.id, self.other_youth_user)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_require_session_access_professional_assigned(self):
        s = require_session_access(self.db, self.sim_session.id, self.prof_user)
        self.assertEqual(s.id, self.sim_session.id)

    def test_require_session_for_start_not_en_curso(self):
        self.sim_session.status = "COMPLETADA"
        self.db.commit()
        with self.assertRaises(HTTPException) as ctx:
            require_session_for_start(self.db, self.sim_session.id, self.youth_user)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_touch_session_heartbeat_updates_timestamp(self):
        self.assertIsNone(self.sim_session.last_heartbeat_at)
        out = touch_session_heartbeat(self.db, self.sim_session.id, self.youth_user)
        self.assertEqual(out, {"ok": True})
        self.db.refresh(self.sim_session)
        self.assertIsNotNone(self.sim_session.last_heartbeat_at)

    def test_touch_session_heartbeat_not_en_curso(self):
        self.sim_session.status = "COMPLETADA"
        self.db.commit()
        out = touch_session_heartbeat(self.db, self.sim_session.id, self.youth_user)
        self.assertEqual(out["ok"], False)
        self.assertEqual(out["status"], "COMPLETADA")


if __name__ == "__main__":
    unittest.main()
