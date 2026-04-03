"""Tests unitarios de app.services.catalogs."""
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.case import Case
from app.models.competency import Competency
from app.models.competency_level import CompetencyLevel
from app.models.job_role import JobRole
from app.models.simulation_template import SimulationTemplate
from app.services.catalogs import (
    competencies_catalog_payload,
    competency_levels_catalog_payload,
    get_simulation_template_by_id,
    list_cases_for_catalog,
    list_job_roles_for_catalog,
    list_simulation_templates_for_catalog,
    parse_competencias,
    resolve_simulation_template_default_case,
    simulation_template_to_response,
)


class ParseCompetenciasTestCase(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(parse_competencias(None))

    def test_list_passthrough(self):
        self.assertEqual(parse_competencias([1, 2]), [1, 2])

    def test_json_array_string(self):
        self.assertEqual(parse_competencias('["a","b"]'), ["a", "b"])

    def test_plain_string_becomes_single_item_list(self):
        self.assertEqual(parse_competencias("comunicación"), ["comunicación"])

    def test_invalid_json_falls_back_to_wrapped_string(self):
        self.assertEqual(parse_competencias("[not json"), ["[not json"])

    def test_non_string_non_list_returns_none(self):
        self.assertIsNone(parse_competencias(42))


class CatalogsDbTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.jr = JobRole(
            slug="dev",
            name="Dev",
            description="d",
            objetivo="o",
            competencias='["c1"]',
            is_active=True,
        )
        self.jr_inactive = JobRole(
            slug="old",
            name="Old",
            description=None,
            objetivo=None,
            competencias=None,
            is_active=False,
        )
        self.case_norm = Case(
            slug="caso-n",
            name="N",
            difficulty="NORMAL",
            prompt_instructions="p",
            is_active=True,
        )
        self.case_alt = Case(
            slug="caso-a",
            name="A",
            difficulty="ALTA",
            prompt_instructions="p",
            is_active=True,
        )
        self.db.add_all([self.jr, self.jr_inactive, self.case_norm, self.case_alt])
        self.db.flush()

        self.tpl = SimulationTemplate(
            job_role_id=self.jr.id,
            case_id=self.case_norm.id,
            liveavatar_context_id="ctx",
            liveavatar_avatar_id="av",
            liveavatar_voice_id="vo",
            is_active=True,
        )
        self.tpl_alt = SimulationTemplate(
            job_role_id=self.jr.id,
            case_id=self.case_alt.id,
            liveavatar_context_id="ctx2",
            liveavatar_avatar_id="av2",
            liveavatar_voice_id="vo2",
            is_active=True,
        )
        self.db.add_all([self.tpl, self.tpl_alt])

        self.comp = Competency(slug="com", name="Comunicación", is_active=True)
        self.comp_inactive = Competency(slug="x", name="X", is_active=False)
        self.level = CompetencyLevel(slug="b", label="Básico", sort_order=2)
        self.level2 = CompetencyLevel(slug="a", label="Alto", sort_order=1)
        self.db.add_all([self.comp, self.comp_inactive, self.level, self.level2])
        self.db.commit()
        self.db.refresh(self.tpl)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_list_job_roles_only_active(self):
        rows = list_job_roles_for_catalog(self.db)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].slug, "dev")
        self.assertEqual(rows[0].competencias, ["c1"])

    def test_list_cases(self):
        rows = list_cases_for_catalog(self.db)
        self.assertEqual(len(rows), 2)
        slugs = {r.slug for r in rows}
        self.assertEqual(slugs, {"caso-n", "caso-a"})

    def test_list_simulation_templates_no_filter(self):
        rows = list_simulation_templates_for_catalog(self.db, None, None)
        self.assertEqual(len(rows), 2)

    def test_list_simulation_templates_filter_job_role(self):
        rows = list_simulation_templates_for_catalog(self.db, self.jr.id, None)
        self.assertEqual(len(rows), 2)

    def test_list_simulation_templates_filter_case(self):
        rows = list_simulation_templates_for_catalog(self.db, None, self.case_norm.id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].case.slug, "caso-n")

    def test_resolve_default_case_prefers_normal(self):
        row = resolve_simulation_template_default_case(self.db, self.jr.id)
        self.assertIsNotNone(row)
        self.assertEqual(row.case.difficulty, "NORMAL")
        self.assertEqual(row.resolution_reason, "DEFAULT_CASE")

    def test_get_simulation_template_by_id(self):
        row = get_simulation_template_by_id(self.db, self.tpl.id)
        self.assertIsNotNone(row)
        self.assertEqual(row.id, self.tpl.id)

    def test_get_simulation_template_by_id_missing(self):
        self.assertIsNone(get_simulation_template_by_id(self.db, 99999))

    def test_simulation_template_to_response_resolution_reason(self):
        self.db.refresh(self.jr)
        self.db.refresh(self.case_norm)
        self.db.refresh(self.tpl)
        r = simulation_template_to_response(self.tpl, self.jr, self.case_norm, resolution_reason="TEST")
        self.assertEqual(r.resolution_reason, "TEST")

    def test_competencies_payload_only_active_ordered(self):
        rows = competencies_catalog_payload(self.db)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["slug"], "com")

    def test_competency_levels_ordered_by_sort_order(self):
        rows = competency_levels_catalog_payload(self.db)
        self.assertEqual([r["slug"] for r in rows], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
