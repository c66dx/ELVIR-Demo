import unittest

from pydantic import ValidationError

from app.config import Settings
from app.schemas.session import SessionCloseRequest, SessionCreate


_PROD_SECRET = "a" * 32  # cumple longitud mínima en producción (distinta del default dev)


class SettingsAndSchemasTestCase(unittest.TestCase):
    def test_auto_create_tables_default_is_false(self):
        s = Settings(CORS_ORIGINS="http://localhost:4200")
        self.assertFalse(s.AUTO_CREATE_TABLES)

    def test_env_must_be_known_value(self):
        with self.assertRaises(ValidationError):
            Settings(ENV="prdo")

    def test_production_alias_is_accepted_when_safe(self):
        s = Settings(
            ENV="production",
            SECRET_KEY=_PROD_SECRET,
            AUTO_CREATE_TABLES=False,
            CORS_ORIGINS="http://localhost:4200",
        )
        self.assertEqual(s.ENV, "prod")

    def test_env_is_trimmed_before_validation(self):
        s = Settings(
            ENV="  prod  ",
            SECRET_KEY=_PROD_SECRET,
            AUTO_CREATE_TABLES=False,
            CORS_ORIGINS="http://localhost:4200",
        )
        self.assertEqual(s.ENV, "prod")

    def test_is_production_flag(self):
        s_prod = Settings(ENV="production", SECRET_KEY=_PROD_SECRET, AUTO_CREATE_TABLES=False, CORS_ORIGINS="http://localhost:4200")
        s_dev = Settings(ENV="dev", CORS_ORIGINS="http://localhost:4200")
        self.assertTrue(s_prod.is_production)
        self.assertFalse(s_dev.is_production)

    def test_production_rejects_default_secret(self):
        with self.assertRaises(ValidationError):
            Settings(ENV="prod", SECRET_KEY="elvir-dev-secret-change-in-production", AUTO_CREATE_TABLES=False)

    def test_production_rejects_auto_create_tables(self):
        with self.assertRaises(ValidationError):
            Settings(ENV="prod", SECRET_KEY=_PROD_SECRET, AUTO_CREATE_TABLES=True)

    def test_production_rejects_short_secret(self):
        with self.assertRaises(ValidationError):
            Settings(
                ENV="prod",
                SECRET_KEY="x" * 31,
                AUTO_CREATE_TABLES=False,
                CORS_ORIGINS="http://localhost:4200",
            )

    def test_storage_s3_requires_bucket_and_public_url(self):
        with self.assertRaises(ValidationError):
            Settings(
                CORS_ORIGINS="http://localhost:4200",
                STORAGE_BACKEND="s3",
                S3_BUCKET="",
                S3_PUBLIC_BASE_URL="https://cdn.example.com",
            )
        with self.assertRaises(ValidationError):
            Settings(
                CORS_ORIGINS="http://localhost:4200",
                STORAGE_BACKEND="s3",
                S3_BUCKET="mi-bucket",
                S3_PUBLIC_BASE_URL="",
            )

    def test_auto_create_tables_allowed_only_in_dev(self):
        Settings(ENV="dev", AUTO_CREATE_TABLES=True, CORS_ORIGINS="http://localhost:4200")

        with self.assertRaises(ValidationError):
            Settings(ENV="staging", AUTO_CREATE_TABLES=True, CORS_ORIGINS="http://localhost:4200")


    def test_cors_origins_requires_valid_value(self):
        with self.assertRaises(ValidationError):
            Settings(CORS_ORIGINS=" ,  , ")

    def test_cors_origins_are_normalized(self):
        s = Settings(CORS_ORIGINS=" http://a.com , ,http://b.com  ")
        self.assertEqual(s.cors_origins_list, ["http://a.com", "http://b.com"])

    def test_cors_origins_strip_trailing_slashes(self):
        s = Settings(CORS_ORIGINS="https://a.com/,https://b.com///")
        self.assertEqual(s.cors_origins_list, ["https://a.com", "https://b.com"])

    def test_cors_origins_are_deduplicated_preserving_order(self):
        s = Settings(CORS_ORIGINS="http://a.com,http://b.com,http://a.com,http://c.com")
        self.assertEqual(s.cors_origins_list, ["http://a.com", "http://b.com", "http://c.com"])


    def test_csrf_defaults_present(self):
        s = Settings(CORS_ORIGINS="http://localhost:4200")
        self.assertEqual(s.CSRF_COOKIE_NAME, "elvir_csrf_token")
        self.assertEqual(s.CSRF_HEADER_NAME, "X-CSRF-Token")

    def test_security_csp_default(self):
        s = Settings(CORS_ORIGINS="http://localhost:4200")
        self.assertIn("default-src 'none'", s.SECURITY_CSP)

    def test_session_mode_validation(self):
        with self.assertRaises(ValidationError):
            SessionCreate(youth_id=1, simulation_template_id=1, mode="INVALIDA")

    def test_session_close_status_validation(self):
        with self.assertRaises(ValidationError):
            SessionCloseRequest(status="EN_CURSO")


if __name__ == "__main__":
    unittest.main()
