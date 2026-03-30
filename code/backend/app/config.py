"""Configuración de la aplicación."""

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env en la raíz del backend (junto a app/)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    """Configuración cargada desde variables de entorno."""

    # Entorno
    ENV: str = "dev"  # dev, staging, prod
    AUTO_CREATE_TABLES: bool = False

    # Logging: LOG_JSON=None -> JSON solo si ENV=prod; en dev/staging texto legible por consola
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool | None = None

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

    # Límite de intentos de login por IP (formato slowapi: "5/minute", "10/second")
    LOGIN_RATE_LIMIT: str = "5/minute"
    # Endpoints públicos de activación (anti enumeración / abuso por IP)
    ACTIVATE_VALIDATE_RATE_LIMIT: str = "30/minute"
    ACTIVATE_ACCOUNT_RATE_LIMIT: str = "10/minute"
    # Cambio de contraseña / email (sesión válida; anti abuso por IP)
    AUTH_ACCOUNT_CHANGE_RATE_LIMIT: str = "15/minute"
    # Subidas: foto de perfil y material (staff)
    PROFILE_PHOTO_RATE_LIMIT: str = "30/minute"
    STAFF_UPLOAD_RATE_LIMIT: str = "40/minute"
    # Panel admin (rutas /admin/*; por IP).
    ADMIN_API_RATE_LIMIT: str = "120/minute"
    # Resto de rutas API sin @limiter explícito (por IP). Las rutas con decorador siguen su propio límite
    DEFAULT_API_RATE_LIMIT: str = "300/minute"
    # Tras proxy inverso de confianza: usar el primer IP de X-Forwarded-For como clave de rate limit
    # En dev dejar en false (un cliente podría falsificar la cabecera si llega directo al API)
    RATE_LIMIT_TRUST_X_FORWARDED_FOR: bool = False

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

    # Ficheros: disco local (`uploads/`) o S3-compatible (escala horizontal)
    STORAGE_BACKEND: str = "local"  # local | s3
    S3_BUCKET: str = ""
    S3_REGION: str = "us-east-1"
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_PUBLIC_BASE_URL: str = ""
    S3_KEY_PREFIX: str = ""

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

    @property
    def use_json_logs(self) -> bool:
        """Salida una-línea JSON (p. ej. para agregadores); si LOG_JSON está fijado, manda sobre ENV."""
        if self.LOG_JSON is not None:
            return self.LOG_JSON
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

        if self.is_production and len(self.SECRET_KEY) < 32:
            raise ValueError(
                "SECRET_KEY debe tener al menos 32 caracteres en producción (p. ej. `openssl rand -hex 32`)"
            )

        if self.AUTO_CREATE_TABLES and self.ENV != "dev":
            raise ValueError("AUTO_CREATE_TABLES solo puede ser True en entorno dev")

        allowed_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        ll = (self.LOG_LEVEL or "INFO").strip().upper()
        if ll not in allowed_levels:
            raise ValueError(f"LOG_LEVEL inválido: use uno de {sorted(allowed_levels)}")
        self.LOG_LEVEL = ll

        sb = (self.STORAGE_BACKEND or "local").strip().lower()
        if sb not in ("local", "s3"):
            raise ValueError("STORAGE_BACKEND debe ser local o s3")
        self.STORAGE_BACKEND = sb
        if sb == "s3":
            if not (self.S3_BUCKET or "").strip():
                raise ValueError("S3_BUCKET es obligatorio cuando STORAGE_BACKEND=s3")
            if not (self.S3_PUBLIC_BASE_URL or "").strip():
                raise ValueError("S3_PUBLIC_BASE_URL es obligatorio cuando STORAGE_BACKEND=s3")
            try:
                import boto3  # noqa: F401
            except ImportError as e:
                raise ValueError("Instala el paquete boto3 para STORAGE_BACKEND=s3") from e

        return self

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
