import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from app.config import settings
from app.database import Base
from app.models.case import Case
from app.models.job_role import JobRole
from app.models.session import Session as SessionModel
from app.models.session_event import SessionEvent
from app.models.session_transcript import SessionTranscript
from app.models.simulation_template import SimulationTemplate
from app.models.user import User
from app.models.youth import Youth
from app.routers.sessions import close_session, get_session_transcript_endpoint, start_session
from app.schemas.session import SessionCloseRequest
from app.services.liveavatar import LiveAvatarError


def _build_request(request_id: str = "req-test"):
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "path": "/api/v1/sessions/1/start",
        "raw_path": b"/api/v1/sessions/1/start",
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


class SessionsLiveAvatarTestCase(unittest.TestCase):
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
        self.db.add(self.user)
        self.db.flush()

        self.youth = Youth(user_id=self.user.id, display_name="Joven", identifier="JOV-001", login_enabled=True, is_active=True)
        self.db.add(self.youth)
        self.db.flush()

        self.job_role = JobRole(slug="operario", name="Operario", description="Desc", objetivo="Obj", competencias="[]", is_active=True)
        self.case = Case(slug="normal", name="Normal", difficulty="NORMAL", prompt_instructions="Instr", is_active=True)
        self.db.add_all([self.job_role, self.case])
        self.db.flush()

        self.template = SimulationTemplate(
            job_role_id=self.job_role.id,
            case_id=self.case.id,
            liveavatar_context_id="ctx-elvir-dinamico",
            liveavatar_avatar_id="avatar-default",
            liveavatar_voice_id="voice-default",
            is_active=True,
        )
        self.db.add(self.template)
        self.db.flush()

        self.session = SessionModel(
            youth_id=self.youth.id,
            professional_id=None,
            simulation_template_id=self.template.id,
            mode="AUTOGESTIONADA",
            status="EN_CURSO",
            started_at=datetime.now(UTC),
        )
        self.db.add(self.session)
        self.db.commit()

        self._settings_backup = (
            settings.LIVEAVATAR_API_KEY,
            settings.LIVEAVATAR_CONTEXT_ID,
            settings.LIVEAVATAR_AVATAR_ID,
            settings.LIVEAVATAR_VOICE_ID,
        )

    def tearDown(self):
        (
            settings.LIVEAVATAR_API_KEY,
            settings.LIVEAVATAR_CONTEXT_ID,
            settings.LIVEAVATAR_AVATAR_ID,
            settings.LIVEAVATAR_VOICE_ID,
        ) = self._settings_backup
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def _event_payload(self, event_type: str):
        ev = (
            self.db.query(SessionEvent)
            .filter(SessionEvent.session_id == self.session.id, SessionEvent.event_type == event_type)
            .first()
        )
        return ev.payload if ev else None

    def test_start_session_fallback_when_not_configured(self):
        settings.LIVEAVATAR_API_KEY = ""
        settings.LIVEAVATAR_CONTEXT_ID = ""
        settings.LIVEAVATAR_AVATAR_ID = ""
        settings.LIVEAVATAR_VOICE_ID = ""

        req = _build_request("req-not-config")
        response = start_session(self.session.id, req, self.user, self.db)

        self.assertIsNotNone(response.embed)
        self.assertIsNone(response.livekit_url)
        self.assertIsNotNone(response.fallback_detail)
        fd = (response.fallback_detail or "").lower()
        self.assertTrue(
            "liveavatar" in fd and ("api_key" in fd or "falta" in fd or "marcador" in fd),
            msg=response.fallback_detail,
        )
        payload = self._event_payload("LIVEAVATAR_FALLBACK")
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("reason"), "NOT_CONFIGURED")
        self.assertEqual(payload.get("request_id"), "req-not-config")
        self.assertIn("config_status", payload)

    def test_start_session_fallback_on_liveavatar_error(self):
        settings.LIVEAVATAR_API_KEY = "key"
        settings.LIVEAVATAR_CONTEXT_ID = "ctx-123"
        settings.LIVEAVATAR_AVATAR_ID = "avatar-123"
        settings.LIVEAVATAR_VOICE_ID = "voice-123"

        req = _build_request("req-error")
        with patch("app.services.liveavatar.start_liveavatar_session", side_effect=LiveAvatarError("boom", 502)):
            response = start_session(self.session.id, req, self.user, self.db)

        self.assertIsNotNone(response.embed)
        self.assertEqual(response.fallback_detail, "boom")
        payload = self._event_payload("LIVEAVATAR_FALLBACK")
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("reason"), "LIVEAVATAR_ERROR")
        self.assertEqual(payload.get("detail"), "boom")
        self.assertEqual(payload.get("request_id"), "req-error")

    def test_start_session_success_uses_livekit_payload(self):
        settings.LIVEAVATAR_API_KEY = "key"
        settings.LIVEAVATAR_CONTEXT_ID = "ctx-123"
        settings.LIVEAVATAR_AVATAR_ID = "avatar-123"
        settings.LIVEAVATAR_VOICE_ID = "voice-123"

        req = _build_request("req-ok")
        with patch(
            "app.services.liveavatar.start_liveavatar_session",
            return_value={
                "session_id": "sess-1",
                "livekit_url": "wss://livekit.example",
                "access_token": "token-123",
            },
        ):
            response = start_session(self.session.id, req, self.user, self.db)

        self.assertIsNone(response.embed)
        self.assertEqual(response.livekit_url, "wss://livekit.example")
        self.assertEqual(response.access_token, "token-123")
        payload = self._event_payload("LIVEAVATAR_FALLBACK")
        self.assertIsNone(payload)

    def test_close_session_persists_transcript_when_available(self):
        self.session.liveavatar_session_id = "live-123"
        self.db.commit()

        transcript_payload = {
            "session_active": False,
            "transcript_data": [
                {
                    "role": "user",
                    "transcript": "Hola",
                    "absolute_timestamp": 100,
                    "relative_timestamp": 1,
                }
            ],
        }

        with patch("app.services.liveavatar.get_session_transcript", return_value=transcript_payload):
            response = close_session(
                self.session.id,
                SessionCloseRequest(status="COMPLETADA", metrics={"duration_seconds": 42}),
                _build_request("req-close"),
                self.user,
                self.db,
            )

        self.assertEqual(response.status, "COMPLETADA")
        self.db.refresh(self.session)
        self.assertEqual(self.session.duration_seconds, 42)

        stored = (
            self.db.query(SessionTranscript)
            .filter(SessionTranscript.session_id == self.session.id)
            .first()
        )
        self.assertIsNotNone(stored)
        self.assertEqual(stored.transcript_data, transcript_payload["transcript_data"])
        self.assertEqual(stored.session_active, transcript_payload["session_active"])

        endpoint = get_session_transcript_endpoint(self.session.id, self.user, self.db)
        self.assertIsNotNone(endpoint)
        dumped = [e.model_dump() for e in endpoint.transcript_data]
        self.assertEqual(dumped, transcript_payload["transcript_data"])

    def test_close_session_ignores_transcript_failure(self):
        self.session.liveavatar_session_id = "live-404"
        self.db.commit()

        with patch("app.services.liveavatar.get_session_transcript", return_value=None):
            response = close_session(
                self.session.id,
                SessionCloseRequest(status="ERROR", motivo="LIVEAVATAR_CONNECTION", metrics={"duration_seconds": 5}),
                _build_request("req-close-error"),
                self.user,
                self.db,
            )

        self.assertEqual(response.status, "ERROR")
        stored = (
            self.db.query(SessionTranscript)
            .filter(SessionTranscript.session_id == self.session.id)
            .first()
        )
        self.assertIsNone(stored)


if __name__ == "__main__":
    unittest.main()
