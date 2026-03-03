"""Configuración de la aplicación."""
from pathlib import Path

from pydantic_settings import BaseSettings

# .env en la raíz del backend (junto a app/)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    """Configuración cargada desde variables de entorno."""

    # Base de datos (PostgreSQL)
    DATABASE_URL: str = "postgresql://elvir:elvir@localhost:5432/elvir"

    # JWT - OBLIGATORIO en producción: generar con `openssl rand -hex 32`
    SECRET_KEY: str = "elvir-dev-secret-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas

    # CORS
    CORS_ORIGINS: str = "http://localhost:4200,http://127.0.0.1:4200"

    # App
    APP_BASE_URL: str = "http://localhost:4200"  # Para activation_url

    # LiveAvatar (Context Dinámico)
    LIVEAVATAR_API_KEY: str = ""
    LIVEAVATAR_AVATAR_ID: str = ""
    LIVEAVATAR_VOICE_ID: str = ""
    LIVEAVATAR_CONTEXT_ID: str = ""
    LIVEAVATAR_API_BASE: str = "https://api.liveavatar.com/v1"

    class Config:
        env_file = str(_ENV_FILE) if _ENV_FILE.exists() else ".env"
        env_file_encoding = "utf-8"


settings = Settings()
