"""Tests de check_youth_access, expire_stale_sessions, build_sessions_query y 404 en require_session_access."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.models.assignment import Assignment
from app.models.case import Case
from app.models.job_role import JobRole
from app.models.professional import Professional
from app.models.session import Session as SessionModel
from app.models.session_event import SessionEvent
from app.models.simulation_template import SimulationTemplate
from app.models.user import User
from app.models.youth import Youth
from app.services.session_access import (
    build_sessions_query,
    check_youth_access,
    expire_stale_sessions,
    require_session_access,
)


class CheckYouthAccessTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.admin = User(email="adm@test.cl", password_hash="x", role="ADMIN", is_active=True)
        self.prof_u = User(email="p@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.youth_u = User(email="j@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.other_j = User(email="j2@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add_all([self.admin, self.prof_u, self.youth_u, self.other_j])
        self.db.flush()

        self.prof = Professional(user_id=self.prof_u.id, display_name="P", is_active=True)
        self.db.add(self.prof)
        self.db.flush()

        self.youth = Youth(
            user_id=self.youth_u.id,
            display_name="Y1",
            identifier="J-1",
            login_enabled=True,
            is_active=True,
        )
        self.other_youth = Youth(
            user_id=self.other_j.id,
            display_name="Y2",
            identifier="J-2",
            login_enabled=True,
            is_active=True,
        )
        self.db.add_all([self.youth, self.other_youth])
        self.db.flush()

        self.db.add(
            Assignment(youth_id=self.youth.id, professional_id=self.prof.id, status="ACTIVO")
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_admin_allowed_when_flag(self):
        self.assertTrue(
            check_youth_access(self.db, self.admin, self.youth.id, allow_admin=True)
        )

    def test_admin_denied_without_flag(self):
        self.assertFalse(check_youth_access(self.db, self.admin, self.youth.id))

    def test_youth_own(self):
        self.assertTrue(check_youth_access(self.db, self.youth_u, self.youth.id))

    def test_youth_other(self):
        self.assertFalse(check_youth_access(self.db, self.youth_u, self.other_youth.id))

    def test_professional_assigned(self):
        self.assertTrue(check_youth_access(self.db, self.prof_u, self.youth.id))

    def test_professional_no_row(self):
        orphan = User(email="po@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.db.add(orphan)
        self.db.commit()
        self.assertFalse(check_youth_access(self.db, orphan, self.youth.id))

    def test_professional_not_assigned(self):
        self.assertFalse(check_youth_access(self.db, self.prof_u, self.other_youth.id))


class ExpireStaleSessionsTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.prof_u = User(email="p@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.youth_u = User(email="j@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add_all([self.prof_u, self.youth_u])
        self.db.flush()
        self.prof = Professional(user_id=self.prof_u.id, display_name="P", is_active=True)
        self.db.add(self.prof)
        self.db.flush()
        self.youth = Youth(
            user_id=self.youth_u.id,
            display_name="Y",
            identifier="J-1",
            login_enabled=True,
            is_active=True,
        )
        self.db.add(self.youth)
        self.db.flush()

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
        self.db.commit()
        self.db.refresh(self.template)

        now = datetime.now(timezone.utc)
        self.stale = SessionModel(
            youth_id=self.youth.id,
            professional_id=self.prof.id,
            simulation_template_id=self.template.id,
            mode="SUPERVISADA",
            status="EN_CURSO",
            started_at=now - timedelta(hours=1),
            last_heartbeat_at=now - timedelta(hours=1),
        )
        self.db.add(self.stale)
        self.db.commit()
        self.db.refresh(self.stale)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_timeout_zero_returns_zero(self):
        with patch.object(settings, "SESSION_IDLE_TIMEOUT_MINUTES", 0):
            self.assertEqual(expire_stale_sessions(self.db), 0)
        self.db.refresh(self.stale)
        self.assertEqual(self.stale.status, "EN_CURSO")

    def test_cancels_stale_session(self):
        with patch.object(settings, "SESSION_IDLE_TIMEOUT_MINUTES", 30):
            n = expire_stale_sessions(self.db)
        self.assertEqual(n, 1)
        self.db.refresh(self.stale)
        self.assertEqual(self.stale.status, "CANCELADA")
        self.assertIsNotNone(self.stale.ended_at)
        self.assertEqual(self.stale.metrics.get("motivo"), "ABANDONO_TIMEOUT")
        ev = self.db.query(SessionEvent).filter(SessionEvent.session_id == self.stale.id).first()
        self.assertIsNotNone(ev)
        self.assertEqual(ev.event_type, "AUTO_CANCELLED")

    def test_no_stale_returns_zero(self):
        self.stale.last_heartbeat_at = datetime.now(timezone.utc)
        self.db.commit()
        with patch.object(settings, "SESSION_IDLE_TIMEOUT_MINUTES", 30):
            self.assertEqual(expire_stale_sessions(self.db), 0)


class BuildSessionsQueryTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.admin = User(email="adm@test.cl", password_hash="x", role="ADMIN", is_active=True)
        self.prof_u = User(email="p@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.youth_u = User(email="j@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add_all([self.admin, self.prof_u, self.youth_u])
        self.db.flush()

        self.prof = Professional(user_id=self.prof_u.id, display_name="P", is_active=True)
        self.db.add(self.prof)
        self.db.flush()

        self.youth = Youth(
            user_id=self.youth_u.id,
            display_name="Y",
            identifier="J-1",
            login_enabled=True,
            is_active=True,
        )
        self.db.add(self.youth)
        self.db.flush()

        self.db.add(Assignment(youth_id=self.youth.id, professional_id=self.prof.id, status="ACTIVO"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_admin_no_youth_filter_returns_none(self):
        self.assertIsNone(build_sessions_query(self.db, self.admin, None))

    def test_youth_without_row_returns_none(self):
        orphan = User(email="jo@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add(orphan)
        self.db.commit()
        self.assertIsNone(build_sessions_query(self.db, orphan, None))

    def test_youth_query_own_sessions(self):
        q = build_sessions_query(self.db, self.youth_u, None)
        self.assertIsNotNone(q)
        self.assertEqual(q.count(), 0)

    def test_professional_without_row_returns_none(self):
        orphan = User(email="pro@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.db.add(orphan)
        self.db.commit()
        self.assertIsNone(build_sessions_query(self.db, orphan, None))

    def test_professional_filters_assigned_youths(self):
        q = build_sessions_query(self.db, self.prof_u, None)
        self.assertIsNotNone(q)
        # subquery exists; count 0 sin sesiones
        self.assertEqual(q.count(), 0)

    def test_youth_id_denied_raises_403(self):
        with self.assertRaises(HTTPException) as ctx:
            build_sessions_query(self.db, self.youth_u, 99999)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_youth_id_allowed_returns_query(self):
        q = build_sessions_query(self.db, self.prof_u, self.youth.id)
        self.assertIsNotNone(q)
        self.assertEqual(q.count(), 0)


class RequireSessionAccess404TestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()
        self.user = User(email="j@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add(self.user)
        self.db.flush()
        self.db.add(
            Youth(
                user_id=self.user.id,
                display_name="Y",
                identifier="J-1",
                login_enabled=True,
                is_active=True,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_session_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            require_session_access(self.db, 99999, self.user)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
