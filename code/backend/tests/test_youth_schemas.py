"""Validación de esquemas de jóvenes."""
import unittest

from pydantic import ValidationError

from app.schemas.youth import YouthBase, YouthCreate, YouthUpdate


class YouthBaseTestCase(unittest.TestCase):
    def test_display_name_trimmed(self):
        m = YouthBase(
            display_name="  Ana  ",
            login_enabled=False,
        )
        self.assertEqual(m.display_name, "Ana")

    def test_rejects_empty_name(self):
        with self.assertRaises(ValidationError):
            YouthBase(display_name="   ", login_enabled=False)

    def test_year_bounds(self):
        with self.assertRaises(ValidationError):
            YouthBase(display_name="x", year_of_birth=1800, login_enabled=False)


class YouthCreateTestCase(unittest.TestCase):
    def test_login_requires_email(self):
        with self.assertRaises(ValidationError):
            YouthCreate(display_name="x", login_enabled=True)


class YouthUpdateTestCase(unittest.TestCase):
    def test_empty_display_rejected(self):
        with self.assertRaises(ValidationError):
            YouthUpdate(display_name="  ")


if __name__ == "__main__":
    unittest.main()
