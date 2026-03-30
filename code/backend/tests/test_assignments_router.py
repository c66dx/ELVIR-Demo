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
from app.routers.assignments import create_assignment, end_assignment
from app.schemas.assignment import AssignmentCreate


class AssignmentsRouterTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.admin_user = User(email="admin@test.cl", password_hash="x", role="ADMIN", is_active=True)
        self.prof_user = User(email="prof@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.other_prof_user = User(email="prof2@test.cl", password_hash="x", role="PROFESIONAL", is_active=True)
        self.db.add_all([self.admin_user, self.prof_user, self.other_prof_user])
        self.db.flush()

        self.prof = Professional(user_id=self.prof_user.id, display_name="Pro 1", is_active=True)
        self.other_prof = Professional(user_id=self.other_prof_user.id, display_name="Pro 2", is_active=True)
        self.db.add_all([self.prof, self.other_prof])
        self.db.flush()

        self.youth = Youth(display_name="Joven", identifier="JOV-001", login_enabled=False, is_active=True)
        self.db.add(self.youth)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_admin_can_create_assignment(self):
        payload = AssignmentCreate(youth_id=self.youth.id, professional_id=self.prof.id)
        result = create_assignment(payload, user=self.admin_user, db=self.db)
        self.assertEqual(result["status"], "ACTIVO")

    def test_professional_can_assign_self_only(self):
        payload = AssignmentCreate(youth_id=self.youth.id, professional_id=self.prof.id)
        result = create_assignment(payload, user=self.prof_user, db=self.db)
        self.assertEqual(result["professional_id"], self.prof.id)

        payload_other = AssignmentCreate(youth_id=self.youth.id, professional_id=self.other_prof.id)
        with self.assertRaises(HTTPException) as ctx:
            create_assignment(payload_other, user=self.prof_user, db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_duplicate_assignment_is_rejected(self):
        payload = AssignmentCreate(youth_id=self.youth.id, professional_id=self.prof.id)
        create_assignment(payload, user=self.admin_user, db=self.db)
        with self.assertRaises(HTTPException) as ctx:
            create_assignment(payload, user=self.admin_user, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_end_assignment_by_professional_or_admin(self):
        payload = AssignmentCreate(youth_id=self.youth.id, professional_id=self.prof.id)
        created = create_assignment(payload, user=self.admin_user, db=self.db)
        assignment_id = created["id"]

        result = end_assignment(assignment_id, user=self.prof_user, db=self.db)
        self.assertEqual(result["status"], "INACTIVO")

        assignment = Assignment(youth_id=self.youth.id, professional_id=self.prof.id, status="ACTIVO")
        self.db.add(assignment)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            end_assignment(assignment.id, user=self.other_prof_user, db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)

        result_admin = end_assignment(assignment.id, user=self.admin_user, db=self.db)
        self.assertEqual(result_admin["status"], "INACTIVO")


if __name__ == "__main__":
    unittest.main()
