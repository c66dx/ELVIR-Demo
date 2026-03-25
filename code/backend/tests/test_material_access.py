import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.user import User
from app.models.youth import Youth
from app.models.professional import Professional
from app.models.support_material import SupportMaterial
from app.models.material_suggestion import MaterialSuggestion
from app.routers.material import list_support_material


class MaterialAccessTestCase(unittest.TestCase):
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

        self.general_material = SupportMaterial(
            title="General",
            description="Gen",
            type="PDF",
            url="https://example.com/gen.pdf",
            created_by=None,
            active=True,
        )
        self.suggested_material = SupportMaterial(
            title="Sugerido",
            description="Sug",
            type="VIDEO",
            url="https://example.com/sug.mp4",
            created_by=self.prof.id,
            active=True,
        )
        self.other_prof_material = SupportMaterial(
            title="Otro Pro",
            description="Otro",
            type="LINK",
            url="https://example.com/otro",
            created_by=self.other_prof.id,
            active=True,
        )
        self.inactive_general = SupportMaterial(
            title="Inactivo",
            description="Off",
            type="PDF",
            url="https://example.com/off.pdf",
            created_by=None,
            active=False,
        )
        self.db.add_all([
            self.general_material,
            self.suggested_material,
            self.other_prof_material,
            self.inactive_general,
        ])
        self.db.flush()

        self.db.add(MaterialSuggestion(
            youth_id=self.youth.id,
            material_id=self.suggested_material.id,
            professional_id=self.prof.id,
        ))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_youth_sees_only_general_and_suggested(self):
        items = list_support_material(
            user=self.youth_user,
            db=self.db,
            job_role_id=None,
            case_id=None,
            page=None,
            page_size=None,
        )
        ids = {item["id"] for item in items}

        self.assertIn(self.general_material.id, ids)
        self.assertIn(self.suggested_material.id, ids)
        self.assertNotIn(self.other_prof_material.id, ids)
        self.assertNotIn(self.inactive_general.id, ids)


if __name__ == "__main__":
    unittest.main()
