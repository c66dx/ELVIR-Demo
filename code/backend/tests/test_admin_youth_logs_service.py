"""Tests de build_youth_logs_response (panel admin)."""
import unittest
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.case import Case
from app.models.job_role import JobRole
from app.models.platform_session import PlatformSession
from app.models.professional import Professional
from app.models.session import Session as SessionModel
from app.models.simulation_template import SimulationTemplate
from app.models.user import User
from app.models.youth import Youth
from app.services.admin_youth_logs_service import build_youth_logs_response


class AdminYouthLogsServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.u_y = User(email="j@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.u_p = User(email="p@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.db.add_all([self.u_y, self.u_p])
        self.db.flush()

        self.prof = Professional(user_id=self.u_p.id, display_name="Doc", is_active=True)
        self.db.add(self.prof)
        self.db.flush()

        self.youth = Youth(
            user_id=self.u_y.id,
            display_name="Y",
            identifier="J-1",
            login_enabled=True,
            is_active=True,
        )
        self.db.add(self.youth)
        self.db.flush()

        self.db.add(PlatformSession(user_id=self.u_y.id))
        self.db.add(PlatformSession(user_id=self.u_y.id))

        self.job = JobRole(
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
        self.db.add_all([self.job, self.case])
        self.db.flush()

        self.tpl = SimulationTemplate(
            job_role_id=self.job.id,
            case_id=self.case.id,
            liveavatar_context_id="ctx",
            liveavatar_avatar_id="av",
            liveavatar_voice_id="vo",
            is_active=True,
        )
        self.db.add(self.tpl)
        self.db.flush()

        self.sim = SessionModel(
            youth_id=self.youth.id,
            professional_id=self.prof.id,
            simulation_template_id=self.tpl.id,
            mode="SUPERVISADA",
            status="COMPLETADA",
        )
        self.db.add(self.sim)
        self.db.commit()
        self.db.refresh(self.youth)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_youth_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            build_youth_logs_response(
                self.db,
                99999,
                platform_page=None,
                platform_page_size=None,
                interviews_page=None,
                interviews_page_size=None,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_lists_platform_and_interviews(self):
        out = build_youth_logs_response(
            self.db,
            self.youth.id,
            platform_page=None,
            platform_page_size=None,
            interviews_page=None,
            interviews_page_size=None,
        )
        self.assertEqual(len(out.platform_sessions), 2)
        self.assertEqual(len(out.interviews), 1)
        self.assertEqual(out.interviews[0].professional_name, "Doc")
        self.assertIsNone(out.meta)

    def test_platform_pagination_without_user_shows_empty_meta(self):
        self.youth.user_id = None
        self.db.commit()
        out = build_youth_logs_response(
            self.db,
            self.youth.id,
            platform_page=1,
            platform_page_size=10,
            interviews_page=None,
            interviews_page_size=None,
        )
        self.assertEqual(out.platform_sessions, [])
        self.assertIsNotNone(out.meta)
        self.assertIsNotNone(out.meta.platform)
        self.assertEqual(out.meta.platform.total, 0)

    def test_interviews_pagination(self):
        out = build_youth_logs_response(
            self.db,
            self.youth.id,
            platform_page=None,
            platform_page_size=None,
            interviews_page=1,
            interviews_page_size=1,
        )
        self.assertEqual(len(out.interviews), 1)
        self.assertIsNotNone(out.meta)
        self.assertIsNotNone(out.meta.interviews)
        self.assertGreaterEqual(out.meta.interviews.total, 1)


class AdminYouthLogsNoUserTestCase(unittest.TestCase):
    """Joven sin cuenta: solo entrevistas."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.u_p = User(email="p@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.db.add(self.u_p)
        self.db.flush()
        self.prof = Professional(user_id=self.u_p.id, display_name="P", is_active=True)
        self.db.add(self.prof)
        self.db.flush()

        self.youth = Youth(
            user_id=None,
            display_name="Sin user",
            identifier="J-N",
            login_enabled=False,
            is_active=True,
        )
        self.db.add(self.youth)
        self.db.flush()

        self.job = JobRole(
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
        self.db.add_all([self.job, self.case])
        self.db.flush()

        self.tpl = SimulationTemplate(
            job_role_id=self.job.id,
            case_id=self.case.id,
            liveavatar_context_id="ctx",
            liveavatar_avatar_id="av",
            liveavatar_voice_id="vo",
            is_active=True,
        )
        self.db.add(self.tpl)
        self.db.flush()

        self.db.add(
            SessionModel(
                youth_id=self.youth.id,
                professional_id=self.prof.id,
                simulation_template_id=self.tpl.id,
                mode="AUTOGESTIONADA",
                status="EN_CURSO",
                started_at=datetime.now(UTC),
            )
        )
        self.db.commit()
        self.db.refresh(self.youth)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_no_platform_sessions(self):
        out = build_youth_logs_response(
            self.db,
            self.youth.id,
            platform_page=None,
            platform_page_size=None,
            interviews_page=None,
            interviews_page_size=None,
        )
        self.assertEqual(out.platform_sessions, [])
        self.assertEqual(len(out.interviews), 1)


if __name__ == "__main__":
    unittest.main()
