#!/usr/bin/env python3
"""Script para poblar la base de datos con datos iniciales (seed)."""
import json
import sys
from pathlib import Path

# Asegurar que el directorio backend está en el path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base
from app.config import settings
from app.models.user import User
from app.models.youth import Youth
from app.models.professional import Professional
from app.models.assignment import Assignment
from app.models.job_role import JobRole
from app.models.case import Case
from app.models.simulation_template import SimulationTemplate
from app.models.support_material import SupportMaterial
from app.core.security import get_password_hash


def seed(db: Session):
    """Ejecuta el seed."""
    # Usuarios
    if db.query(User).count() == 0:
        users = [
            User(email="joven1@test.cl", password_hash=get_password_hash("test123"), role="JOVEN", is_active=True),
            User(email="joven2@test.cl", password_hash=get_password_hash("test123"), role="JOVEN", is_active=True),
            User(email="prof@test.cl", password_hash=get_password_hash("test123"), role="PROFESIONAL", is_active=True),
            User(email="admin@test.cl", password_hash=get_password_hash("test123"), role="ADMIN", is_active=True),
        ]
        for u in users:
            db.add(u)
        db.flush()
    else:
        # Asegurar que existe Admin aunque el seed ya se ejecutó antes
        admin_user = db.query(User).filter(User.role == "ADMIN").first()
        if not admin_user:
            admin_user = User(email="admin@test.cl", password_hash=get_password_hash("test123"), role="ADMIN", is_active=True)
            db.add(admin_user)
            db.flush()

    # Profesional
    prof_user = db.query(User).filter(User.email == "prof@test.cl").first()
    prof = None
    if prof_user and db.query(Professional).count() == 0:
        prof = Professional(user_id=prof_user.id, display_name="Profesional Test", is_active=True)
        db.add(prof)
        db.flush()
    elif prof_user:
        prof = db.query(Professional).filter(Professional.user_id == prof_user.id).first()

    # Jóvenes
    if db.query(Youth).count() == 0:
        u1 = db.query(User).filter(User.email == "joven1@test.cl").first()
        u2 = db.query(User).filter(User.email == "joven2@test.cl").first()
        youths = [
            Youth(user_id=u1.id, login_enabled=True, display_name="María González", identifier="JOV-001",
                  phone="+56912345678", is_active=True, general_notes="Notas generales"),
            Youth(user_id=u2.id, login_enabled=False, display_name="Juan Rodríguez", identifier="JOV-002",
                  is_active=True),
            Youth(login_enabled=True, display_name="Carolina Flores", identifier="JOV-003", is_active=True),
            Youth(login_enabled=True, display_name="Roberto Díaz", identifier="JOV-004", is_active=True),
        ]
        for y in youths:
            db.add(y)
        db.flush()
        for y in youths:
            if prof:
                db.add(Assignment(youth_id=y.id, professional_id=prof.id, status="ACTIVO"))

    # Job roles (contenido de Catalina - Context Dinámico)
    if db.query(JobRole).count() == 0:
        roles = [
            JobRole(slug="operario", name="Operario",
                    description="Ejecutar tareas operativas conforme a procedimientos establecidos, asegurando eficiencia, seguridad y calidad en los procesos productivos o de servicio.",
                    objetivo="Evaluar competencias para rol operario.",
                    competencias=json.dumps(["Responsabilidad", "Trabajo en equipo", "Cumplimiento de normas", "Gestión del tiempo", "Atención al detalle"]),
                    is_active=True),
            JobRole(slug="atencion-publico", name="Atención de Público",
                    description="Atender y orientar a clientes o usuarios, gestionando consultas, reclamos y solicitudes de manera eficiente y cordial.",
                    objetivo="Evaluar habilidades para puesto de atención al público.",
                    competencias=json.dumps(["Comunicación efectiva", "Empatía", "Orientación al cliente", "Resolución de conflictos", "Manejo del estrés"]),
                    is_active=True),
            JobRole(slug="administrativo", name="Administrativo",
                    description="Gestionar y ejecutar procesos administrativos y documentales, brindando soporte operativo a las distintas áreas.",
                    objetivo="Evaluar competencias para rol administrativo.",
                    competencias=json.dumps(["Organización", "Gestión documental", "Comunicación formal", "Planificación", "Atención al detalle"]),
                    is_active=True),
            JobRole(slug="tecnico-profesional", name="Técnico-Profesional",
                    description="Desarrollar funciones técnicas especializadas, aplicando conocimientos profesionales para resolver problemas operativos.",
                    objetivo="Evaluar presentación de competencias técnicas.",
                    competencias=json.dumps(["Pensamiento analítico", "Resolución de problemas técnicos", "Autonomía", "Responsabilidad profesional", "Mejora continua"]),
                    is_active=True),
        ]
        for r in roles:
            db.add(r)
        db.flush()

    # Cases (contenido de Catalina - 4 niveles de dificultad)
    if db.query(Case).count() == 0:
        cases = [
            Case(slug="normal", name="Entrevista Normal", difficulty="NORMAL",
                 prompt_instructions="Entrevista estándar. Mantener tono profesional y empático. Preguntas típicas de selección. Plantear preguntas abiertas que inviten a reflexionar. Permitir presentación relativamente libre, interviniendo con repreguntas para ordenar el relato.",
                 is_active=True),
            Case(slug="baja", name="Dificultad Baja (empático)", difficulty="BAJA",
                 prompt_instructions="Entrevistadora muy empática y acogedora. Dar más tiempo para responder. Refuerzo positivo frecuente. Ritmo pausado y contenedor. Formular preguntas concretas y guiadas. Evitar preguntas abiertas extensas. Priorizar claridad básica.",
                 is_active=True),
            Case(slug="media", name="Dificultad Media (guiada)", difficulty="MEDIA",
                 prompt_instructions="Nivel medio de apoyo. Guiar con preguntas abiertas. Ofrecer ejemplos si el candidato duda. Solicitar ejemplos específicos y profundizar con repreguntas estructuradas. Permitir presentación relativamente libre, interviniendo para ordenar el relato.",
                 is_active=True),
            Case(slug="alta", name="Dificultad Alta (poco empático)", difficulty="ALTA",
                 prompt_instructions="Entrevistadora más directa y con menos paciencia. Preguntas más desafiantes. Menos refuerzo. Estilo exigente. Plantear preguntas abiertas orientadas al análisis. Explorar criterios, prioridades y reflexiones del candidato.",
                 is_active=True),
        ]
        for c in cases:
            db.add(c)
        db.flush()

    # Simulation templates (16 = 4 cargos × 4 casos). Context Dinámico: mismo context_id para todos.
    if db.query(SimulationTemplate).count() == 0:
        roles = db.query(JobRole).all()
        cases = db.query(Case).all()
        # Placeholder; el valor real viene de LIVEAVATAR_CONTEXT_ID en .env
        ctx_id = "ctx-elvir-dinamico"
        avatar_id = "avatar-default"
        voice_id = "voice-default"
        for jr in roles:
            for c in cases:
                db.add(SimulationTemplate(
                    job_role_id=jr.id, case_id=c.id,
                    liveavatar_context_id=ctx_id,
                    liveavatar_avatar_id=avatar_id,
                    liveavatar_voice_id=voice_id,
                    is_active=True,
                ))
        db.flush()

    # Support material
    if db.query(SupportMaterial).count() == 0:
        jr1 = db.query(JobRole).filter(JobRole.slug == "operario").first()
        c1 = db.query(Case).filter(Case.slug == "normal").first()
        materials = [
            SupportMaterial(title="Técnicas de comunicación", description="Guía básica", type="VIDEO",
                            url="https://example.com/v1", job_role_id=jr1.id if jr1 else None,
                            case_id=c1.id if c1 else None, active=True),
            SupportMaterial(title="Lenguaje corporal", type="PDF", url="https://example.com/p1",
                            job_role_id=jr1.id if jr1 else None, active=True),
            SupportMaterial(title="Preguntas frecuentes retail", type="VIDEO", url="https://example.com/v2",
                            case_id=c1.id if c1 else None, active=True),
            SupportMaterial(title="Introducción a entrevistas", type="LINK", url="https://example.com/l1",
                            active=True),
        ]
        for m in materials:
            db.add(m)

    db.commit()
    print("Seed completado correctamente.")


def run_migrations():
    """Ejecuta migraciones manuales (columnas nuevas en SQLite)."""
    from sqlalchemy import text
    if "sqlite" not in settings.DATABASE_URL:
        return
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE support_material ADD COLUMN created_by INTEGER"))
            conn.commit()
    except Exception:
        pass  # Columna ya existe


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    run_migrations()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
