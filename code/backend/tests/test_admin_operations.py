"""Tests de admin_operations (borrados admin, delete_upload_file)."""
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.assignment import Assignment
from app.models.professional import Professional
from app.models.professional_invitation import ProfessionalInvitation
from app.models.user import User
from app.models.youth import Youth
from app.services.admin_operations import (
    apply_admin_soft_delete_professional,
    apply_admin_soft_delete_youth,
    apply_hard_delete_youth,
    delete_upload_file,
)


class DeleteUploadFileTestCase(unittest.TestCase):
    def test_none_url(self):
        self.assertFalse(delete_upload_file(None, "/uploads/youths/", Path(".")))

    def test_wrong_prefix(self):
        self.assertFalse(
            delete_upload_file("http://x/uploads/other/f.jpg", "/uploads/youths/", Path("."))
        )

    def test_deletes_existing_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "photo.jpg").write_bytes(b"x")
            url = "http://localhost:8000/uploads/youths/photo.jpg"
            self.assertTrue(delete_upload_file(url, "/uploads/youths/", base))
            self.assertFalse((base / "photo.jpg").exists())


class AdminSoftDeleteTestCase(unittest.TestCase):
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
        self.u_j = User(email="j@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add_all([self.u_p, self.u_j])
        self.db.flush()

        self.prof = Professional(user_id=self.u_p.id, display_name="P", is_active=True)
        self.db.add(self.prof)
        self.db.flush()

        self.youth = Youth(
            user_id=self.u_j.id,
            display_name="Y",
            identifier="J-1",
            login_enabled=True,
            is_active=True,
        )
        self.db.add(self.youth)
        self.db.flush()

        self.db.add(
            Assignment(youth_id=self.youth.id, professional_id=self.prof.id, status="ACTIVO")
        )
        self.db.add(
            ProfessionalInvitation(
                professional_id=self.prof.id,
                email="inv@test.cl",
                token="tok-inv",
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_soft_delete_youth(self):
        apply_admin_soft_delete_youth(self.db, self.youth.id)
        y = self.db.query(Youth).filter(Youth.id == self.youth.id).first()
        self.assertFalse(y.is_active)
        self.assertFalse(y.login_enabled)
        a = self.db.query(Assignment).filter(Assignment.youth_id == self.youth.id).first()
        self.assertEqual(a.status, "INACTIVO")

    def test_soft_delete_professional(self):
        apply_admin_soft_delete_professional(self.db, self.prof.id)
        p = self.db.query(Professional).filter(Professional.id == self.prof.id).first()
        self.assertFalse(p.is_active)
        u = self.db.query(User).filter(User.id == self.u_p.id).first()
        self.assertFalse(u.is_active)
        self.assertIn("disabled+", u.email)


class HardDeleteYouthTestCase(unittest.TestCase):
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

    def test_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            apply_hard_delete_youth(self.db, 99999)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_conflict_same_user_professional_and_youth(self):
        u = User(email="both@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add(u)
        self.db.flush()
        prof = Professional(user_id=u.id, display_name="P", is_active=True)
        self.db.add(prof)
        self.db.flush()
        y = Youth(user_id=u.id, display_name="Y", identifier="J-X", login_enabled=True, is_active=True)
        self.db.add(y)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            apply_hard_delete_youth(self.db, y.id)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_hard_delete_minimal_youth_and_user(self):
        u = User(email="solo@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add(u)
        self.db.flush()
        y = Youth(user_id=u.id, display_name="S", identifier="J-S", login_enabled=True, is_active=True)
        self.db.add(y)
        self.db.commit()
        yid = y.id
        uid = u.id

        out = apply_hard_delete_youth(self.db, yid)
        self.assertTrue(out["ok"])
        self.assertEqual(self.db.query(Youth).filter(Youth.id == yid).count(), 0)
        self.assertEqual(self.db.query(User).filter(User.id == uid).count(), 0)


if __name__ == "__main__":
    unittest.main()
