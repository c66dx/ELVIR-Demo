"""Tests de normalización de RUT chileno."""
import unittest

from fastapi import HTTPException

from app.services.youth_rut import normalize_rut


class NormalizeRutTestCase(unittest.TestCase):
    def test_valid_formats(self):
        self.assertEqual(normalize_rut("12345678-5"), "12.345.678-5")
        self.assertEqual(normalize_rut("12.345.678-5"), "12.345.678-5")
        self.assertEqual(normalize_rut("123456785"), "12.345.678-5")

    def test_invalid_dv(self):
        with self.assertRaises(HTTPException) as ctx:
            normalize_rut("12345678-0")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_too_short(self):
        with self.assertRaises(HTTPException) as ctx:
            normalize_rut("1")
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
