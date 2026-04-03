"""Tests unitarios de la política de longitud de contraseña (configurable)."""

import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.config import settings
from app.core import password_policy


class PasswordPolicyTestCase(unittest.TestCase):
    def test_min_password_length_reads_settings(self):
        with patch.object(settings, "PASSWORD_MIN_LENGTH", 10):
            self.assertEqual(password_policy.min_password_length(), 10)

    def test_raise_if_password_too_short_ok(self):
        with patch.object(settings, "PASSWORD_MIN_LENGTH", 4):
            password_policy.raise_if_password_too_short("abcd")

    def test_raise_if_password_too_short_raises(self):
        with patch.object(settings, "PASSWORD_MIN_LENGTH", 8):
            with self.assertRaises(HTTPException) as ctx:
                password_policy.raise_if_password_too_short("short")
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("8", ctx.exception.detail)

    def test_activation_password_error_code(self):
        with patch.object(settings, "PASSWORD_MIN_LENGTH", 6):
            self.assertIsNone(password_policy.activation_password_error_code(None))
            self.assertIsNone(password_policy.activation_password_error_code(""))
            self.assertIsNone(password_policy.activation_password_error_code("   "))
            self.assertEqual(
                password_policy.activation_password_error_code("12345"),
                "PASSWORD_TOO_SHORT",
            )
            self.assertIsNone(password_policy.activation_password_error_code("123456"))


if __name__ == "__main__":
    unittest.main()
