"""Aplicación FastAPI ELVIR."""
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base, get_db
from app.routers import auth, youths, catalogs, sessions, material, summaries, professionals, upload


def create_tables():
    """Crea las tablas en la BD."""
    Base.metadata.create_all(bind=engine)
    _migrate_profile_checklist()
    _migrate_support_material_created_by()


def _migrate_profile_checklist():
    """Añade columna profile_checklist a youths si no existe (SQLite)."""
    if "sqlite" not in settings.DATABASE_URL:
        return
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE youths ADD COLUMN profile_checklist TEXT"))
            conn.commit()
    except Exception:
        pass  # Columna ya existe


def _migrate_support_material_created_by():
    """Añade columna created_by a support_material si no existe (SQLite)."""
    if "sqlite" not in settings.DATABASE_URL:
        return
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE support_material ADD COLUMN created_by INTEGER"))
            conn.commit()
    except Exception:
        pass  # Columna ya existe


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield
    # cleanup si hace falta


app = FastAPI(
    title="ELVIR API",
    description="API REST del backend ELVIR - Plataforma de simulaciones de entrevistas laborales",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(youths.router, prefix="/api/v1")
app.include_router(catalogs.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(material.router, prefix="/api/v1")
app.include_router(summaries.router, prefix="/api/v1")
app.include_router(professionals.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")

# Carpeta de archivos subidos
uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/")
def root():
    return {"message": "ELVIR API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
