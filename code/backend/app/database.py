"""Configuración de base de datos con SQLAlchemy."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

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
