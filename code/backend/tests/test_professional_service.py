"""Tests unitarios de professional_service."""
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
from app.services.professional_service import (
    create_professional_with_invitation,
    fetch_professional_assignments,
    get_professional_by_id,
    get_user_by_id,
    professional_response_dict,
    query_professionals_admin,
    update_professional_admin,
    user_map_by_ids,
)


class ProfessionalServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.u_p = User(email="prof@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.db.add(self.u_p)
        self.db.flush()
        self.prof = Professional(
            user_id=self.u_p.id,
            display_name="Doc",
            specialty="s",
            institution="i",
            is_active=True,
        )
        self.db.add(self.prof)
        self.db.flush()

        self.u_j = User(email="j@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add(self.u_j)
        self.db.flush()
        self.youth = Youth(
            user_id=self.u_j.id,
            display_name="J",
            identifier="J-1",
            login_enabled=True,
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
        self.db.refresh(self.prof)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_fetch_assignments_no_pagination(self):
        rows, headers = fetch_professional_assignments(self.db, self.prof.id, None, None)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(headers)
        self.assertEqual(rows[0]["youth_id"], self.youth.id)

    def test_fetch_assignments_with_pagination(self):
        rows, headers = fetch_professional_assignments(self.db, self.prof.id, 1, 10)
        self.assertEqual(headers["X-Total-Count"], "1")
        self.assertEqual(len(rows), 1)

    def test_query_professionals_admin_active_filter(self):
        pros, h = query_professionals_admin(self.db, is_active=True, page=None, page_size=None)
        self.assertEqual(len(pros), 1)
        pros_off, _ = query_professionals_admin(self.db, is_active=False, page=None, page_size=None)
        self.assertEqual(len(pros_off), 0)

    def test_query_professionals_pagination(self):
        pros, h = query_professionals_admin(self.db, None, page=1, page_size=1)
        self.assertIsNotNone(h)
        self.assertEqual(h["X-Total-Count"], "1")

    def test_user_map_by_ids(self):
        self.assertEqual(user_map_by_ids(self.db, []), {})
        m = user_map_by_ids(self.db, [self.u_p.id])
        self.assertEqual(m[self.u_p.id].email, "prof@test.cl")

    def test_professional_response_dict(self):
        d = professional_response_dict(self.prof, self.u_p)
        self.assertEqual(d["id"], self.prof.id)
        self.assertEqual(d["display_name"], "Doc")

    def test_get_professional_by_id(self):
        self.assertIsNotNone(get_professional_by_id(self.db, self.prof.id))
        self.assertIsNone(get_professional_by_id(self.db, 99999))

    def test_get_user_by_id(self):
        self.assertIsNone(get_user_by_id(self.db, None))
        self.assertEqual(get_user_by_id(self.db, self.u_p.id).email, "prof@test.cl")

    def test_create_professional_with_invitation(self):
        prof, user, url = create_professional_with_invitation(
            self.db,
            email="nuevo@test.cl",
            display_name="Nuevo",
            specialty=None,
            institution=None,
            app_base_url="http://app.test",
        )
        self.assertTrue(url.startswith("http://app.test/activar?token="))
        self.assertFalse(user.is_active)
        self.assertEqual(prof.display_name, "Nuevo")

    def test_create_professional_duplicate_email(self):
        with self.assertRaises(HTTPException) as ctx:
            create_professional_with_invitation(
                self.db,
                email="prof@test.cl",
                display_name="Dup",
                specialty=None,
                institution=None,
                app_base_url="http://x",
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_update_professional_admin(self):
        p, u = update_professional_admin(
            self.db,
            self.prof.id,
            display_name="Renombrado",
            specialty="sp",
            institution=None,
            is_active=True,
        )
        self.assertEqual(p.display_name, "Renombrado")
        self.assertEqual(u.email, "prof@test.cl")

    def test_update_professional_deactivates_user(self):
        update_professional_admin(
            self.db,
            self.prof.id,
            display_name="Doc",
            specialty=None,
            institution=None,
            is_active=False,
        )
        u = self.db.query(User).filter(User.id == self.u_p.id).first()
        self.assertFalse(u.is_active)

    def test_update_professional_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            update_professional_admin(
                self.db,
                99999,
                display_name="x",
                specialty=None,
                institution=None,
                is_active=None,
            )
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
