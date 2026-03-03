"""Configuración de base de datos con SQLAlchemy (PostgreSQL)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.config import settings

_is_sqlite = "sqlite" in settings.DATABASE_URL
_engine_kwargs: dict = {
    "echo": False,
    "connect_args": {"check_same_thread": False} if _is_sqlite else {},
}
if _is_sqlite and ":memory:" in settings.DATABASE_URL:
    # SQLite :memory: requiere StaticPool para que todas las conexiones compartan la misma BD
    _engine_kwargs["poolclass"] = StaticPool
else:
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["pool_size"] = 10
engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base para todos los modelos."""

    pass


def get_db():
    """Dependency para obtener sesión de BD."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
