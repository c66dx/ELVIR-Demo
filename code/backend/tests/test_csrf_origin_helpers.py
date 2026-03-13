import unittest

from app.config import settings
from app.core.middleware import _extract_origin_from_referer, _is_allowed_origin, _normalize_origin


class CsrfOriginHelpersTestCase(unittest.TestCase):
    def test_normalize_origin_removes_default_ports(self):
        self.assertEqual(_normalize_origin("http://example.com:80"), "http://example.com")
        self.assertEqual(_normalize_origin("https://example.com:443"), "https://example.com")

    def test_normalize_origin_keeps_custom_port(self):
        self.assertEqual(_normalize_origin("http://example.com:8080"), "http://example.com:8080")

    def test_normalize_origin_lowercases_scheme_and_host(self):
        self.assertEqual(_normalize_origin("HTTPS://EXAMPLE.COM:443"), "https://example.com")
        self.assertEqual(_normalize_origin("HTTP://Example.com:80"), "http://example.com")

    def test_normalize_origin_rejects_invalid_origin(self):
        self.assertIsNone(_normalize_origin("not-an-origin"))
        self.assertIsNone(_normalize_origin(""))
        self.assertIsNone(_normalize_origin(None))

    def test_normalize_origin_rejects_invalid_port(self):
        self.assertIsNone(_normalize_origin("https://example.com:abc"))
        self.assertIsNone(_normalize_origin("https://example.com:99999"))

    def test_normalize_origin_rejects_userinfo(self):
        self.assertIsNone(_normalize_origin("https://user@example.com"))
        self.assertIsNone(_normalize_origin("https://user:pass@example.com"))

    def test_normalize_origin_rejects_unsupported_scheme(self):
        self.assertIsNone(_normalize_origin("ftp://example.com"))
        self.assertIsNone(_normalize_origin("file://localhost/tmp"))

    def test_extract_origin_from_referer(self):
        self.assertEqual(
            _extract_origin_from_referer("https://example.com/path?x=1"),
            "https://example.com",
        )

    def test_is_allowed_origin_ignores_malformed_entries_in_allowlist(self):
        original = settings.CORS_ORIGINS
        try:
            settings.CORS_ORIGINS = "https://example.com,not-an-origin,ftp://ignored"
            self.assertTrue(_is_allowed_origin("https://example.com"))
            self.assertFalse(_is_allowed_origin("https://evil.example"))
        finally:
            settings.CORS_ORIGINS = original

    def test_is_allowed_origin_accepts_uppercase_input(self):
        allowed = settings.cors_origins_list[0]
        self.assertTrue(_is_allowed_origin(allowed.upper()))

    def test_is_allowed_origin_accepts_trailing_slash_and_rejects_unknown(self):
        allowed = settings.cors_origins_list[0]
        self.assertTrue(_is_allowed_origin(allowed + "/"))
        self.assertFalse(_is_allowed_origin("https://evil.example"))


if __name__ == "__main__":
    unittest.main()
