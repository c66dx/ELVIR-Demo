import unittest

from fastapi import HTTPException
from starlette.requests import Request

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.user import User
from app.models.youth import Youth
from app.models.professional import Professional
from app.models.assignment import Assignment
from app.models.job_role import JobRole
from app.models.case import Case
from app.models.simulation_template import SimulationTemplate
from app.routers.sessions import create_session
from app.schemas.session import SessionCreate


def _build_request(request_id: str = "req-test"):
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "path": "/api/v1/sessions",
        "raw_path": b"/api/v1/sessions",
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "root_path": "",
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    req = Request(scope, receive)
    req.state.request_id = request_id
    return req


class SessionsCreateTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.prof_user = User(email="prof@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.other_prof_user = User(email="prof2@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.youth_user = User(email="joven@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add_all([self.prof_user, self.other_prof_user, self.youth_user])
        self.db.flush()

        self.prof = Professional(user_id=self.prof_user.id, display_name="Pro 1", is_active=True)
        self.other_prof = Professional(user_id=self.other_prof_user.id, display_name="Pro 2", is_active=True)
        self.db.add_all([self.prof, self.other_prof])
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

        self.db.add(Assignment(youth_id=self.youth.id, professional_id=self.prof.id, status="ACTIVO"))

        self.job_role = JobRole(
            slug="operario",
            name="Operario",
            description="Desc",
            objetivo="Obj",
            competencias="[]",
            is_active=True,
        )
        self.case = Case(
            slug="normal",
            name="Normal",
            difficulty="NORMAL",
            prompt_instructions="Instr",
            is_active=True,
        )
        self.db.add_all([self.job_role, self.case])
        self.db.flush()

        self.template = SimulationTemplate(
            job_role_id=self.job_role.id,
            case_id=self.case.id,
            liveavatar_context_id="ctx-1",
            liveavatar_avatar_id="avatar-1",
            liveavatar_voice_id="voice-1",
            is_active=True,
        )
        self.db.add(self.template)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_create_session_supervisada_normalizes_professional_id(self):
        data = SessionCreate(
            youth_id=self.youth.id,
            simulation_template_id=self.template.id,
            mode="SUPERVISADA",
            professional_id=None,
        )
        session = create_session(data, _build_request(), self.prof_user, self.db)
        self.assertEqual(session.professional_id, self.prof.id)

    def test_create_session_supervisada_rejects_mismatch_professional_id(self):
        data = SessionCreate(
            youth_id=self.youth.id,
            simulation_template_id=self.template.id,
            mode="SUPERVISADA",
            professional_id=self.other_prof.id,
        )
        with self.assertRaises(HTTPException) as ctx:
            create_session(data, _build_request(), self.prof_user, self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_create_session_autogestionada_rejects_professional_id(self):
        data = SessionCreate(
            youth_id=self.youth.id,
            simulation_template_id=self.template.id,
            mode="AUTOGESTIONADA",
            professional_id=self.prof.id,
        )
        with self.assertRaises(HTTPException) as ctx:
            create_session(data, _build_request(), self.youth_user, self.db)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_create_session_supervisada_requires_professional_role(self):
        data = SessionCreate(
            youth_id=self.youth.id,
            simulation_template_id=self.template.id,
            mode="SUPERVISADA",
            professional_id=None,
        )
        with self.assertRaises(HTTPException) as ctx:
            create_session(data, _build_request(), self.youth_user, self.db)
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
