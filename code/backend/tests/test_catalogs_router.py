import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.case import Case
from app.models.job_role import JobRole
from app.models.simulation_template import SimulationTemplate
from app.models.user import User
from app.routers.catalogs import get_simulation_template, list_simulation_templates, resolve_simulation_template


class CatalogsRouterTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.user = User(email="user@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add(self.user)
        self.db.flush()

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

    def test_list_simulation_templates_returns_joined_refs(self):
        items = list_simulation_templates(user=self.user, db=self.db, job_role_id=None, case_id=None)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].job_role.id, self.job_role.id)
        self.assertEqual(items[0].case.id, self.case.id)

    def test_get_simulation_template_by_id(self):
        item = get_simulation_template(self.template.id, user=self.user, db=self.db)
        self.assertIsNotNone(item)
        self.assertEqual(item.job_role.id, self.job_role.id)
        self.assertEqual(item.case.id, self.case.id)

    def test_resolve_simulation_template_normal_case(self):
        item = resolve_simulation_template(self.job_role.id, user=self.user, db=self.db)
        self.assertIsNotNone(item)
        self.assertEqual(item.job_role.id, self.job_role.id)
        self.assertEqual(item.case.difficulty, "NORMAL")


if __name__ == "__main__":
    unittest.main()
