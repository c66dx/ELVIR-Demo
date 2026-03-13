import unittest

from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.assignment import Assignment
from app.models.professional import Professional
from app.models.session import Session as SessionModel
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation
from app.routers.youths import (
    _create_youth_with_unique_identifier,
    _get_last_session_map,
    _generate_identifier,
    change_youth_email,
    list_youths,
)
from app.schemas.youth import YouthChangeEmailRequest


class YouthsRouterTestCase(unittest.TestCase):
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
        self.youth_user = User(email="joven-old@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.admin_user = User(email="admin@test.cl", password_hash="x", role="ADMIN", is_active=True)
        self.db.add_all([self.prof_user, self.youth_user, self.admin_user])
        self.db.flush()

        self.prof = Professional(user_id=self.prof_user.id, display_name="Pro", is_active=True)
        self.db.add(self.prof)
        self.db.flush()

        self.youth = Youth(user_id=self.youth_user.id, display_name="Joven", identifier="JOV-001", login_enabled=True, is_active=True)
        self.db.add(self.youth)
        self.db.flush()

        self.db.add(Assignment(youth_id=self.youth.id, professional_id=self.prof.id, status="ACTIVO"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()


    def test_generate_identifier_uses_latest_jov_pattern(self):
        self.assertEqual(_generate_identifier(self.db), "JOV-002")

        extra = Youth(user_id=None, display_name="Otro2", identifier="JOV-099", login_enabled=False, is_active=True)
        self.db.add(extra)
        self.db.commit()

        self.assertEqual(_generate_identifier(self.db), "JOV-100")

    def test_generate_identifier_skips_malformed_latest(self):
        malformed = Youth(user_id=None, display_name="Malformed", identifier="JOV-XYZ", login_enabled=False, is_active=True)
        valid = Youth(user_id=None, display_name="Valid", identifier="JOV-010", login_enabled=False, is_active=True)
        self.db.add_all([malformed, valid])
        self.db.commit()

        self.assertEqual(_generate_identifier(self.db), "JOV-011")

    def test_generate_identifier_uses_numeric_max_not_lexicographic(self):
        self.db.add_all([
            Youth(user_id=None, display_name="A", identifier="JOV-100", login_enabled=False, is_active=True),
            Youth(user_id=None, display_name="B", identifier="JOV-099", login_enabled=False, is_active=True),
        ])
        self.db.commit()

        self.assertEqual(_generate_identifier(self.db), "JOV-101")

    def test_get_last_session_map_returns_latest_session(self):
        now = datetime.now(timezone.utc)
        older = SessionModel(
            youth_id=self.youth.id,
            professional_id=self.prof.id,
            simulation_template_id=1,
            mode="SUPERVISADA",
            status="COMPLETADA",
            started_at=now - timedelta(hours=1),
        )
        latest = SessionModel(
            youth_id=self.youth.id,
            professional_id=self.prof.id,
            simulation_template_id=1,
            mode="SUPERVISADA",
            status="COMPLETADA",
            started_at=now,
        )
        self.db.add_all([older, latest])
        self.db.commit()

        last_map = _get_last_session_map(self.db, [self.youth.id])
        self.assertIn(self.youth.id, last_map)
        self.assertEqual(last_map[self.youth.id].id, latest.id)


    def test_get_last_session_map_resolves_tie_with_highest_id(self):
        now = datetime.now(timezone.utc)
        first = SessionModel(
            youth_id=self.youth.id,
            professional_id=self.prof.id,
            simulation_template_id=1,
            mode="SUPERVISADA",
            status="COMPLETADA",
            started_at=now,
        )
        second = SessionModel(
            youth_id=self.youth.id,
            professional_id=self.prof.id,
            simulation_template_id=1,
            mode="SUPERVISADA",
            status="COMPLETADA",
            started_at=now,
        )
        self.db.add_all([first, second])
        self.db.commit()

        last_map = _get_last_session_map(self.db, [self.youth.id])
        self.assertEqual(last_map[self.youth.id].id, max(first.id, second.id))

    def test_change_email_creates_invitation_without_updating_user_email(self):
        response = change_youth_email(
            youth_id=self.youth.id,
            data=YouthChangeEmailRequest(new_email="nuevo@test.cl"),
            prof=self.prof,
            db=self.db,
        )

        self.db.refresh(self.youth_user)
        self.assertEqual(self.youth_user.email, "joven-old@test.cl")

        invitation = (
            self.db.query(YouthInvitation)
            .filter(YouthInvitation.youth_id == self.youth.id, YouthInvitation.email == "nuevo@test.cl")
            .first()
        )
        self.assertIsNotNone(invitation)
        self.assertIsNotNone(response.activation_url)


    def test_change_email_invalidates_previous_pending_invitations(self):
        old_inv = YouthInvitation(
            youth_id=self.youth.id,
            email="old-pending@test.cl",
            token="old-token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.db.add(old_inv)
        self.db.commit()

        change_youth_email(
            youth_id=self.youth.id,
            data=YouthChangeEmailRequest(new_email="nuevo2@test.cl"),
            prof=self.prof,
            db=self.db,
        )

        old = self.db.query(YouthInvitation).filter(YouthInvitation.id == old_inv.id).first()
        self.assertIsNotNone(old)
        self.assertIsNotNone(old.used_at)

        pending = (
            self.db.query(YouthInvitation)
            .filter(YouthInvitation.youth_id == self.youth.id, YouthInvitation.used_at.is_(None))
            .all()
        )
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].email, "nuevo2@test.cl")


    def test_create_youth_with_unique_identifier_retries_on_collision(self):
        self.db.add(Youth(user_id=None, display_name="Dup", identifier="JOV-002", login_enabled=False, is_active=True))
        self.db.commit()

        with patch("app.routers.youths._generate_identifier", side_effect=["JOV-002", "JOV-003"]):
            youth = _create_youth_with_unique_identifier(
                self.db,
                display_name="Nuevo",
                phone=None,
                login_enabled=False,
                general_notes=None,
                profile_checklist_json=None,
            )

        self.db.commit()
        self.assertEqual(youth.identifier, "JOV-003")

    def test_create_youth_with_unique_identifier_raises_after_max_retries(self):
        self.db.add(Youth(user_id=None, display_name="Dup", identifier="JOV-002", login_enabled=False, is_active=True))
        self.db.commit()

        with patch("app.routers.youths._generate_identifier", return_value="JOV-002"):
            with self.assertRaisesRegex(HTTPException, "No fue posible generar un identificador único"):
                _create_youth_with_unique_identifier(
                    self.db,
                    display_name="Nuevo",
                    phone=None,
                    login_enabled=False,
                    general_notes=None,
                    profile_checklist_json=None,
                )

    def test_list_youths_admin_can_list_all(self):
        other_youth = Youth(user_id=None, display_name="Otro", identifier="JOV-002", login_enabled=False, is_active=True)
        self.db.add(other_youth)
        self.db.commit()

        items = list_youths(user=self.admin_user, db=self.db)
        ids = {i.id for i in items}

        self.assertIn(self.youth.id, ids)
        self.assertIn(other_youth.id, ids)

    def test_list_youths_admin_filters_are_applied(self):
        active_match = Youth(user_id=None, display_name="Ana Match", identifier="JOV-010", login_enabled=True, is_active=True)
        inactive_match = Youth(user_id=None, display_name="Ana Off", identifier="JOV-011", login_enabled=True, is_active=False)
        active_other = Youth(user_id=None, display_name="Luis", identifier="JOV-012", login_enabled=False, is_active=True)
        self.db.add_all([active_match, inactive_match, active_other])
        self.db.commit()

        items = list_youths(
            user=self.admin_user,
            db=self.db,
            search="Ana",
            is_active=True,
            login_enabled=True,
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, active_match.id)



if __name__ == "__main__":
    unittest.main()
