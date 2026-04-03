"""Configuración global de pytest: BD aislada para toda la suite."""
import os

# Debe aplicarse antes de que `app.database` cree el engine al importar `app.main`.
# Si DATABASE_URL ya está definida (p. ej. CI con PostgreSQL), no sobrescribir.
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
# Evitar 429 en tests por rate limit (slowapi).
os.environ["LOGIN_RATE_LIMIT"] = "1000/minute"
os.environ["ACTIVATE_VALIDATE_RATE_LIMIT"] = "1000/minute"
os.environ["ACTIVATE_ACCOUNT_RATE_LIMIT"] = "1000/minute"
os.environ["AUTH_ACCOUNT_CHANGE_RATE_LIMIT"] = "1000/minute"
os.environ["PROFILE_PHOTO_RATE_LIMIT"] = "1000/minute"
os.environ["STAFF_UPLOAD_RATE_LIMIT"] = "1000/minute"
os.environ["ADMIN_API_RATE_LIMIT"] = "1000/minute"
os.environ["DEFAULT_API_RATE_LIMIT"] = "100000/minute"
