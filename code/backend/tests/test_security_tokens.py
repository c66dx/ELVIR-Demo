import unittest
from datetime import timedelta

from app.core.security import (
    create_access_token,
    create_csrf_token,
    decode_csrf_token,
    decode_token,
)


class SecurityTokensTestCase(unittest.TestCase):
    def test_access_token_roundtrip(self):
        token = create_access_token({"sub": "42", "role": "ADMIN"})
        payload = decode_token(token)

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.get("sub"), "42")
        self.assertEqual(payload.get("role"), "ADMIN")
        self.assertIsNotNone(payload.get("iat"))

    def test_csrf_token_roundtrip(self):
        token = create_csrf_token(subject="42")
        payload = decode_csrf_token(token)

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.get("sub"), "42")
        self.assertEqual(payload.get("type"), "csrf")

    def test_decode_csrf_token_rejects_access_token(self):
        access = create_access_token({"sub": "42", "role": "ADMIN"})

        self.assertIsNone(decode_csrf_token(access))

    def test_decode_token_returns_none_for_expired_access(self):
        expired = create_access_token(
            {"sub": "42", "role": "ADMIN"},
            expires_delta=timedelta(seconds=-1),
        )

        self.assertIsNone(decode_token(expired))

    def test_decode_csrf_token_returns_none_for_expired_token(self):
        expired = create_csrf_token(
            subject="42",
            expires_delta=timedelta(seconds=-1),
        )

        self.assertIsNone(decode_csrf_token(expired))


if __name__ == "__main__":
    unittest.main()
