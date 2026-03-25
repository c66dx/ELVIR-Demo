import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.user import User
from app.models.youth import Youth
from app.models.job_role import JobRole
from app.models.case import Case
from app.models.simulation_template import SimulationTemplate
from app.models.session import Session as SessionModel
from app.routers.sessions import get_session_context


class SessionsContextTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.user = User(email="joven@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.other_user = User(email="otro@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add_all([self.user, self.other_user])
        self.db.flush()

        self.youth = Youth(
            user_id=self.user.id,
            display_name="Joven",
            identifier="JOV-001",
            login_enabled=True,
            is_active=True,
        )
        self.other_youth = Youth(
            user_id=self.other_user.id,
            display_name="Otro",
            identifier="JOV-002",
            login_enabled=True,
            is_active=True,
        )
        self.db.add_all([self.youth, self.other_youth])
        self.db.flush()

        job_role = JobRole(
            slug="operario",
            name="Operario",
            description="Desc",
            objetivo="Obj",
            competencias="[]",
            is_active=True,
        )
        case = Case(
            slug="normal",
            name="Normal",
            difficulty="NORMAL",
            prompt_instructions="Instr",
            is_active=True,
        )
        self.db.add_all([job_role, case])
        self.db.flush()

        template = SimulationTemplate(
            job_role_id=job_role.id,
            case_id=case.id,
            liveavatar_context_id="ctx-1",
            liveavatar_avatar_id="avatar-1",
            liveavatar_voice_id="voice-1",
            is_active=True,
        )
        self.db.add(template)
        self.db.flush()

        self.session = SessionModel(
            youth_id=self.youth.id,
            professional_id=None,
            simulation_template_id=template.id,
            mode="AUTOGESTIONADA",
            status="EN_CURSO",
        )
        self.db.add(self.session)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_get_session_context_returns_names(self):
        ctx = get_session_context(self.session.id, user=self.user, db=self.db)
        self.assertEqual(ctx["jobRoleName"], "Operario")
        self.assertEqual(ctx["caseName"], "Normal")

    def test_get_session_context_denies_other_user(self):
        with self.assertRaises(HTTPException) as ctx:
            get_session_context(self.session.id, user=self.other_user, db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
