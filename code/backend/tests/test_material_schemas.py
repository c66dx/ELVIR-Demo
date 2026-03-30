"""Validación de esquemas de material de apoyo."""
import unittest

from pydantic import ValidationError

from app.schemas.material import CreateMaterialRequest, SuggestMaterialRequest


class CreateMaterialRequestTestCase(unittest.TestCase):
    def test_valid(self):
        m = CreateMaterialRequest(
            title="  Guía  ",
            description="  ",
            type="PDF",
            url=" https://x.cl/a.pdf ",
            job_role_id=1,
        )
        self.assertEqual(m.title, "Guía")
        self.assertIsNone(m.description)
        self.assertEqual(m.url, "https://x.cl/a.pdf")

    def test_type_literal(self):
        with self.assertRaises(ValidationError):
            CreateMaterialRequest(
                title="t",
                type="DOC",
                url="https://x.cl",
            )

    def test_title_empty(self):
        with self.assertRaises(ValidationError):
            CreateMaterialRequest(title="   ", type="LINK", url="https://x.cl")


class SuggestMaterialRequestTestCase(unittest.TestCase):
    def test_ids_positive(self):
        with self.assertRaises(ValidationError):
            SuggestMaterialRequest(youth_id=0, material_id=1)

    def test_reason_stripped(self):
        m = SuggestMaterialRequest(youth_id=1, material_id=2, reason="  ok  ")
        self.assertEqual(m.reason, "ok")


if __name__ == "__main__":
    unittest.main()
