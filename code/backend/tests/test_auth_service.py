"""Tests unitarios de auth_service (login, me, platform session, validación de token)."""
import unittest
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash, verify_password
from app.database import Base
from app.models.platform_session import PlatformSession
from app.models.professional import Professional
from app.models.professional_invitation import ProfessionalInvitation
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation
from app.schemas.auth import (
    ActivateRequest,
    ChangeEmailRequest,
    ChangePasswordRequest,
    LoginRequest,
)
from app.services.auth_service import (
    activate_account,
    build_me_response,
    change_password,
    end_active_platform_session,
    login_user,
    request_email_change,
    validate_activation_token,
)


class AuthServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_login_success(self):
        u = User(
            email="ok@test.cl",
            password_hash=get_password_hash("secret123"),
            role="PROFESIONAL",
            is_active=True,
        )
        self.db.add(u)
        self.db.flush()
        self.db.add(Professional(user_id=u.id, display_name="P", is_active=True))
        self.db.commit()
        self.db.refresh(u)

        resp, csrf = login_user(self.db, LoginRequest(email="ok@test.cl", password="secret123"))
        self.assertEqual(resp.user_id, u.id)
        self.assertEqual(resp.role, "PROFESIONAL")
        self.assertTrue(resp.access_token)
        self.assertTrue(csrf)

        ps = self.db.query(PlatformSession).filter(PlatformSession.user_id == u.id).first()
        self.assertIsNotNone(ps)
        self.assertIsNone(ps.ended_at)

    def test_login_wrong_password(self):
        u = User(
            email="bad@test.cl",
            password_hash=get_password_hash("secret123"),
            role="PROFESIONAL",
            is_active=True,
        )
        self.db.add(u)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            login_user(self.db, LoginRequest(email="bad@test.cl", password="wrong"))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_login_youth_login_disabled(self):
        u = User(
            email="off@test.cl",
            password_hash=get_password_hash("secret123"),
            role="JOVEN",
            is_active=True,
        )
        self.db.add(u)
        self.db.flush()
        self.db.add(
            Youth(
                user_id=u.id,
                display_name="J",
                identifier="JOV-X",
                login_enabled=False,
                is_active=True,
            )
        )
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            login_user(self.db, LoginRequest(email="off@test.cl", password="secret123"))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_build_me_response_professional(self):
        u = User(email="m@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.db.add(u)
        self.db.flush()
        p = Professional(user_id=u.id, display_name="P", is_active=True)
        self.db.add(p)
        self.db.commit()
        self.db.refresh(u)
        self.db.refresh(p)

        me = build_me_response(self.db, u)
        self.assertEqual(me.professional_id, p.id)
        self.assertIsNone(me.youth_id)

    def test_end_active_platform_session(self):
        u = User(email="ps@test.cl", password_hash="x", role="ADMIN", is_active=True)
        self.db.add(u)
        self.db.flush()
        ps = PlatformSession(user_id=u.id)
        self.db.add(ps)
        self.db.commit()
        self.db.refresh(ps)

        end_active_platform_session(self.db, u)
        self.db.refresh(ps)
        self.assertIsNotNone(ps.ended_at)

    def test_validate_activation_token_youth_invitation(self):
        y = Youth(
            user_id=None,
            display_name="Nuevo",
            identifier="JOV-N",
            login_enabled=False,
            is_active=True,
        )
        self.db.add(y)
        self.db.flush()
        inv = YouthInvitation(
            youth_id=y.id,
            email="inv@test.cl",
            token="tok-youth-1",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        self.db.add(inv)
        self.db.commit()

        v = validate_activation_token(self.db, "tok-youth-1")
        self.assertTrue(v.valid)
        self.assertEqual(v.email, "inv@test.cl")
        self.assertEqual(v.display_name, "Nuevo")

    def test_validate_activation_token_not_found(self):
        v = validate_activation_token(self.db, "no-existe")
        self.assertFalse(v.valid)
        self.assertEqual(v.error, "TOKEN_NOT_FOUND")

    def test_validate_activation_token_professional_invitation(self):
        u = User(email="profu@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.db.add(u)
        self.db.flush()
        p = Professional(user_id=u.id, display_name="Prof", is_active=True)
        self.db.add(p)
        self.db.flush()
        inv = ProfessionalInvitation(
            professional_id=p.id,
            email="profinv@test.cl",
            token="tok-prof-1",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        self.db.add(inv)
        self.db.commit()

        v = validate_activation_token(self.db, "tok-prof-1")
        self.assertTrue(v.valid)
        self.assertEqual(v.email, "profinv@test.cl")
        self.assertEqual(v.display_name, "Prof")


class ActivateAccountTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_activate_youth_first_invitation_creates_user(self):
        y = Youth(
            user_id=None,
            display_name="N",
            identifier="J-N",
            login_enabled=False,
            is_active=True,
        )
        self.db.add(y)
        self.db.flush()
        inv = YouthInvitation(
            youth_id=y.id,
            email="nuevo@test.cl",
            token="tok-act-y",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        self.db.add(inv)
        self.db.commit()

        r = activate_account(
            self.db, ActivateRequest(token="tok-act-y", password="secret123")
        )
        self.assertTrue(r.success)
        self.db.refresh(y)
        self.assertIsNotNone(y.user_id)
        u = self.db.query(User).filter(User.id == y.user_id).first()
        self.assertEqual(u.email, "nuevo@test.cl")
        self.assertEqual(u.role, "JOVEN")

    def test_activate_youth_token_used(self):
        y = Youth(
            user_id=None,
            display_name="N",
            identifier="J-U",
            login_enabled=False,
            is_active=True,
        )
        self.db.add(y)
        self.db.flush()
        inv = YouthInvitation(
            youth_id=y.id,
            email="u@test.cl",
            token="tok-used",
            expires_at=datetime.now(UTC) + timedelta(days=1),
            used_at=datetime.now(UTC),
        )
        self.db.add(inv)
        self.db.commit()

        r = activate_account(self.db, ActivateRequest(token="tok-used", password="x"))
        self.assertFalse(r.success)
        self.assertEqual(r.error, "TOKEN_USED")

    def test_activate_professional_inactive_user(self):
        u = User(
            email="pend@test.cl",
            password_hash=get_password_hash("temp"),
            role="PROFESIONAL",
            is_active=False,
        )
        self.db.add(u)
        self.db.flush()
        p = Professional(user_id=u.id, display_name="P", is_active=True)
        self.db.add(p)
        self.db.flush()
        inv = ProfessionalInvitation(
            professional_id=p.id,
            email="pend@test.cl",
            token="tok-act-p",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        self.db.add(inv)
        self.db.commit()

        r = activate_account(
            self.db, ActivateRequest(token="tok-act-p", password="activated1")
        )
        self.assertTrue(r.success)
        self.db.refresh(u)
        self.assertTrue(u.is_active)


class ChangePasswordAndEmailTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_change_password_success(self):
        u = User(
            email="cp@test.cl",
            password_hash=get_password_hash("oldpass1"),
            role="JOVEN",
            is_active=True,
        )
        self.db.add(u)
        self.db.commit()

        out = change_password(
            self.db,
            u,
            ChangePasswordRequest(current_password="oldpass1", new_password="newpass1"),
        )
        self.assertTrue(out["success"])
        self.db.refresh(u)
        self.assertTrue(verify_password("newpass1", u.password_hash))

    def test_change_password_too_short(self):
        u = User(
            email="s@test.cl",
            password_hash=get_password_hash("oldpass1"),
            role="JOVEN",
            is_active=True,
        )
        self.db.add(u)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            change_password(
                self.db,
                u,
                ChangePasswordRequest(current_password="oldpass1", new_password="12345"),
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_change_password_wrong_current(self):
        u = User(
            email="w@test.cl",
            password_hash=get_password_hash("right"),
            role="JOVEN",
            is_active=True,
        )
        self.db.add(u)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            change_password(
                self.db,
                u,
                ChangePasswordRequest(current_password="wrong", new_password="newpass1"),
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_request_email_change_youth(self):
        u = User(
            email="old@test.cl",
            password_hash=get_password_hash("pw1234"),
            role="JOVEN",
            is_active=True,
        )
        self.db.add(u)
        self.db.flush()
        self.db.add(
            Youth(
                user_id=u.id,
                display_name="Y",
                identifier="J-E",
                login_enabled=True,
                is_active=True,
            )
        )
        self.db.commit()

        r = request_email_change(
            self.db,
            u,
            ChangeEmailRequest(new_email="newmail@test.cl", current_password="pw1234"),
        )
        self.assertTrue(r.success)
        self.assertIn("activar?token=", r.activation_url or "")

    def test_request_email_change_admin_forbidden(self):
        u = User(
            email="adm@test.cl",
            password_hash=get_password_hash("pw"),
            role="ADMIN",
            is_active=True,
        )
        self.db.add(u)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            request_email_change(
                self.db,
                u,
                ChangeEmailRequest(new_email="x@test.cl", current_password="pw"),
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_request_email_change_duplicate_email(self):
        u1 = User(
            email="a@test.cl",
            password_hash=get_password_hash("p1"),
            role="JOVEN",
            is_active=True,
        )
        u2 = User(
            email="b@test.cl",
            password_hash=get_password_hash("p2"),
            role="JOVEN",
            is_active=True,
        )
        self.db.add_all([u1, u2])
        self.db.flush()
        self.db.add(
            Youth(user_id=u1.id, display_name="Y1", identifier="J1", login_enabled=True, is_active=True)
        )
        self.db.add(
            Youth(user_id=u2.id, display_name="Y2", identifier="J2", login_enabled=True, is_active=True)
        )
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            request_email_change(
                self.db,
                u1,
                ChangeEmailRequest(new_email="b@test.cl", current_password="p1"),
            )
        self.assertEqual(ctx.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
