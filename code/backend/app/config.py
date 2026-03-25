"""Configuración de la aplicación."""
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

# .env en la raíz del backend (junto a app/)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    """Configuración cargada desde variables de entorno."""

    # Entorno
    ENV: str = "dev"  # dev, staging, prod
    AUTO_CREATE_TABLES: bool = False

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
    SESSION_IDLE_TIMEOUT_MINUTES: int = 5

    SECURITY_CSP: str = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    AUTH_COOKIE_NAME: str = "elvir_access_token"
    CSRF_COOKIE_NAME: str = "elvir_csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"

    # LiveAvatar (Context Dinámico)
    LIVEAVATAR_API_KEY: str = ""
    LIVEAVATAR_AVATAR_ID: str = ""
    LIVEAVATAR_VOICE_ID: str = ""
    LIVEAVATAR_CONTEXT_ID: str = ""
    LIVEAVATAR_API_BASE: str = "https://api.liveavatar.com/v1"
    LIVEAVATAR_WEBHOOK_SECRET: str = ""

    # Prompt dinámico (endpoint externo)
    PROMPT_PROVIDER: str = "local"  # local | endpoint | script
    PROMPT_ENDPOINT_BASE: str = ""
    PROMPT_ENDPOINT_INTERVENIR_PATH: str = "prompt/generate"
    PROMPT_ENDPOINT_EVALUAR_PATH: str = "prompt/evaluate"
    PROMPT_ENDPOINT_INTERVENIR_URL: str = ""
    PROMPT_ENDPOINT_EVALUAR_URL: str = ""
    PROMPT_ENDPOINT_API_KEY: str = ""
    PROMPT_ENDPOINT_API_KEY_HEADER: str = "Authorization"
    PROMPT_ENDPOINT_API_KEY_PREFIX: str = "Bearer"
    PROMPT_ENDPOINT_TIMEOUT_S: int = 15
    PROMPT_STORE_RAW: bool = False

    # Prompt dinámico (script local)
    PROMPT_SCRIPT_INTERVENIR_CMD: str = ""
    PROMPT_SCRIPT_EVALUAR_CMD: str = ""
    PROMPT_SCRIPT_TIMEOUT_S: int = 15


    @property
    def cors_origins_list(self) -> list[str]:
        """Orígenes CORS normalizados, deduplicados y sin entradas vacías."""
        cleaned = [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()]
        # Eliminar duplicados preservando el orden de primera aparicion
        return list(dict.fromkeys(cleaned))


    @property
    def is_production(self) -> bool:
        """Indica si la app está corriendo en modo producción canónico."""
        return self.ENV == "prod"

    @model_validator(mode="after")
    def validate_production_settings(self):
        """Valida configuraciones críticas para producción."""
        if not self.cors_origins_list:
            raise ValueError("CORS_ORIGINS debe contener al menos un origen válido")

        env = (self.ENV or "").strip().lower()
        alias = {"production": "prod"}
        env = alias.get(env, env)

        allowed_envs = {"dev", "staging", "prod"}
        if env not in allowed_envs:
            raise ValueError("ENV inválido. Usa: dev, staging, prod o production")

        self.ENV = env

        if self.is_production and self.SECRET_KEY == "elvir-dev-secret-change-in-production":
            raise ValueError("SECRET_KEY por defecto no permitido en producción")

        if self.AUTO_CREATE_TABLES and self.ENV != "dev":
            raise ValueError("AUTO_CREATE_TABLES solo puede ser True en entorno dev")
        return self

    class Config:
        env_file = str(_ENV_FILE) if _ENV_FILE.exists() else ".env"
        env_file_encoding = "utf-8"


settings = Settings()

