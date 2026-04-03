"""Validación del cuerpo POST /sessions/{id}/summary."""
import unittest

from pydantic import ValidationError

from app.schemas.summary import SummaryRequest


class SummaryRequestValidationTestCase(unittest.TestCase):
    def test_accepts_text_and_tags(self):
        m = SummaryRequest(
            summary_text="  Buen desempeño en comunicación.  ",
            competency_tags=["  escucha activa  ", "Escucha activa", "empatía"],
        )
        self.assertTrue(m.summary_text.startswith("Buen desempeño"))
        self.assertEqual(m.competency_tags, ["escucha activa", "empatía"])

    def test_rejects_empty_after_strip(self):
        with self.assertRaises(ValidationError):
            SummaryRequest(summary_text="   \n\t  ")

    def test_rejects_too_long(self):
        with self.assertRaises(ValidationError):
            SummaryRequest(summary_text="x" * 100_001)

    def test_tags_none_ok(self):
        m = SummaryRequest(summary_text="Ok")
        self.assertIsNone(m.competency_tags)


if __name__ == "__main__":
    unittest.main()
