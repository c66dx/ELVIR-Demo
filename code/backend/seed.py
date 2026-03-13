#!/usr/bin/env python3
"""Script para poblar la base de datos con datos iniciales (carga inicial)."""
import json
import sys
from pathlib import Path
# Asegurar que el directorio backend esta en la ruta
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base
from app.models.user import User
from app.models.youth import Youth
from app.models.professional import Professional
from app.models.assignment import Assignment
from app.models.job_role import JobRole
from app.models.case import Case
from app.models.simulation_template import SimulationTemplate
from app.models.support_material import SupportMaterial
from app.models.session_transcript import SessionTranscript  # noqa: F401
from app.models.competency import Competency
from app.models.competency_level import CompetencyLevel
from app.models.platform_session import PlatformSession  # noqa: F401 - asegurar tabla creada por create_all
from app.core.security import get_password_hash


def seed(db: Session):
    """Ejecuta la carga inicial."""
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
# Asegurar que existe Admin aunque la carga inicial ya se ejecuto antes
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

    # JÃ³venes
    if db.query(Youth).count() == 0:
        u1 = db.query(User).filter(User.email == "joven1@test.cl").first()
        u2 = db.query(User).filter(User.email == "joven2@test.cl").first()
        youths = [
            Youth(user_id=u1.id, login_enabled=True, display_name="MarÃ­a GonzÃ¡lez", identifier="JOV-001",
                  phone="+56912345678", is_active=True, general_notes="Notas generales"),
            Youth(user_id=u2.id, login_enabled=False, display_name="Juan RodrÃ­guez", identifier="JOV-002",
                  is_active=True),
            Youth(login_enabled=True, display_name="Carolina Flores", identifier="JOV-003", is_active=True),
            Youth(login_enabled=True, display_name="Roberto DÃ­az", identifier="JOV-004", is_active=True),
        ]
        for y in youths:
            db.add(y)
        db.flush()
        for y in youths:
            if prof:
                db.add(Assignment(youth_id=y.id, professional_id=prof.id, status="ACTIVO"))
# Cargos (contenido de Catalina - cargos.json + Context Dinamico roles-data)
    if db.query(JobRole).count() == 0:
        roles = [
            JobRole(slug="operario", name="Operario",
                    description="El cargo de Operario estÃ¡ orientado a la realizaciÃ³n de tareas operativas bÃ¡sicas dentro de la organizaciÃ³n, siguiendo instrucciones y procedimientos definidos. El rol requiere responsabilidad, cumplimiento de normas y capacidad para trabajar de manera organizada y colaborativa.",
                    objetivo="Ejecutar tareas operativas conforme a procedimientos establecidos, asegurando eficiencia, seguridad y calidad en los procesos productivos o de servicio.",
                    competencias=json.dumps(["Responsabilidad", "Trabajo en equipo", "Cumplimiento de normas y procedimientos", "GestiÃ³n del tiempo", "AtenciÃ³n al detalle"]),
                    is_active=True),
            JobRole(slug="atencion-publico", name="AtenciÃ³n de PÃºblico",
                    description="El cargo de AtenciÃ³n de PÃºblico tiene como objetivo atender y orientar a personas usuarias o clientes, brindando respuestas claras y oportunas segÃºn los lineamientos establecidos. El rol demanda habilidades de comunicaciÃ³n, trato cordial y adecuada gestiÃ³n de situaciones diversas.",
                    objetivo="Atender y orientar a clientes o usuarios, gestionando consultas, reclamos y solicitudes de manera eficiente y cordial, contribuyendo a una experiencia de servicio de calidad.",
                    competencias=json.dumps(["ComunicaciÃ³n efectiva", "EmpatÃ­a", "OrientaciÃ³n al cliente", "ResoluciÃ³n de conflictos", "Manejo del estrÃ©s"]),
                    is_active=True),
            JobRole(slug="administrativo", name="Administrativo",
                    description="El cargo Administrativo se enfoca en apoyar la gestiÃ³n interna de la organizaciÃ³n mediante la ejecuciÃ³n de tareas administrativas y de apoyo documental. El rol requiere organizaciÃ³n, orden, cumplimiento de procedimientos y manejo bÃ¡sico de herramientas de oficina.",
                    objetivo="Gestionar y ejecutar procesos administrativos y documentales, brindando soporte operativo a las distintas Ã¡reas de la organizaciÃ³n.",
                    competencias=json.dumps(["OrganizaciÃ³n", "GestiÃ³n documental", "ComunicaciÃ³n formal", "PlanificaciÃ³n", "AtenciÃ³n al detalle"]),
                    is_active=True),
            JobRole(slug="tecnico-profesional", name="TÃ©cnico-Profesional",
                    description="El cargo TÃ©cnico Profesional estÃ¡ orientado al desarrollo de funciones tÃ©cnicas o especializadas dentro de un Ã¡rea especÃ­fica. El rol implica aplicar conocimientos profesionales, cumplir estÃ¡ndares definidos y aportar al correcto funcionamiento de los procesos del Ã¡rea.",
                    objetivo="Desarrollar funciones tÃ©cnicas especializadas, aplicando conocimientos profesionales para resolver problemas operativos y asegurar el cumplimiento de estÃ¡ndares tÃ©cnicos y normativos.",
                    competencias=json.dumps(["Pensamiento analÃ­tico", "ResoluciÃ³n de problemas tÃ©cnicos", "AutonomÃ­a", "Responsabilidad profesional", "Mejora continua"]),
                    is_active=True),
        ]
        for r in roles:
            db.add(r)
        db.flush()
# Casos (contenido de Catalina - indicaciones.json, mapeo: baja->apoyo_regulacion, media->alta_estructuracion, alta->exigencia_alta)
    if db.query(Case).count() == 0:
        cases = [
            Case(slug="normal", name="Entrevista Normal", difficulty="NORMAL",
                 prompt_instructions="Realiza preguntas abiertas y complejas. Invita a profundizar y a reflexionar, manteniendo el foco en el mensaje central. MantÃ©n un estilo de entrevista normal. Introduce referencias a la discapacidad de manera acotada. Refuerza las respuestas adecuadas y ayuda a reformular cuando la presentaciÃ³n pierde foco o impacto.",
                 is_active=True),
            Case(slug="baja", name="Dificultad Baja (empÃ¡tico)", difficulty="BAJA",
                 prompt_instructions="Adopta un tono muy acogedor y contenedor. Valida explÃ­citamente cÃ³mo se puede estar sintiendo la persona. Realiza preguntas muy simples y concretas. Da tiempo suficiente para responder y ofrece pausas. Refuerza cualquier intento de respuesta. Prioriza la sensaciÃ³n de seguridad y contenciÃ³n por sobre el contenido de la entrevista.",
                 is_active=True),
            Case(slug="media", name="Dificultad Media (guiada)", difficulty="MEDIA",
                 prompt_instructions="Formula preguntas muy guiadas y acotadas. Repite o reformula la pregunta si es necesario. Ayuda explÃ­citamente a ordenar la respuesta, indicando quÃ© tipo de informaciÃ³n se espera. MantÃ©n un estilo de entrevista normal. Introduce referencias a la discapacidad de manera acotada. Refuerza las respuestas adecuadas y ayuda a reformular cuando la presentaciÃ³n pierde foco o impacto.",
                 is_active=True),
            Case(slug="alta", name="Dificultad Alta (poco empÃ¡tico)", difficulty="ALTA",
                 prompt_instructions="Realiza preguntas abiertas y complejas. Invita a profundizar y a reflexionar, manteniendo el foco en el mensaje central. Utiliza un estilo de entrevista realista. Introduce preguntas o comentarios directos y poco empÃ¡ticos sobre la discapacidad cuando corresponda y evalÃºa la capacidad de sostener una presentaciÃ³n estratÃ©gica sin intervenir. Debes ser poco empÃ¡tico, muy serio y con poco tino.",
                 is_active=True),
        ]
        for c in cases:
            db.add(c)
        db.flush()
# Plantillas de simulacion (16 = 4 cargos x 4 casos). Context Dinamico: mismo context_id para todos.
    if db.query(SimulationTemplate).count() == 0:
        roles = db.query(JobRole).all()
        cases = db.query(Case).all()
# Marcador de posicion; el valor real viene de LIVEAVATAR_CONTEXT_ID en .env
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

    # Competencias y niveles
    if db.query(Competency).count() == 0:
        competencies = [
            Competency(slug="comunicacion", name="ComunicaciÃ³n", is_active=True),
            Competency(slug="regulacion_emocional", name="RegulaciÃ³n emocional", is_active=True),
            Competency(slug="trabajo_equipo", name="Trabajo en equipo", is_active=True),
            Competency(slug="organizacion", name="OrganizaciÃ³n", is_active=True),
            Competency(slug="autonomia", name="AutonomÃ­a", is_active=True),
        ]
        for c in competencies:
            db.add(c)
        db.flush()
    if db.query(CompetencyLevel).count() == 0:
        levels = [
            CompetencyLevel(slug="BAJO", label="Bajo", sort_order=1),
            CompetencyLevel(slug="MEDIO", label="Medio", sort_order=2),
            CompetencyLevel(slug="ALTO", label="Alto", sort_order=3),
        ]
        for l in levels:
            db.add(l)
        db.flush()
# Material de apoyo
    if db.query(SupportMaterial).count() == 0:
        jr1 = db.query(JobRole).filter(JobRole.slug == "operario").first()
        c1 = db.query(Case).filter(Case.slug == "normal").first()
        materials = [
            SupportMaterial(title="TÃ©cnicas de comunicaciÃ³n", description="GuÃ­a bÃ¡sica", type="VIDEO",
                            url="https://example.com/v1", job_role_id=jr1.id if jr1 else None,
                            case_id=c1.id if c1 else None, active=True),
            SupportMaterial(title="Lenguaje corporal", type="PDF", url="https://example.com/p1",
                            job_role_id=jr1.id if jr1 else None, active=True),
            SupportMaterial(title="Preguntas frecuentes retail", type="VIDEO", url="https://example.com/v2",
                            case_id=c1.id if c1 else None, active=True),
            SupportMaterial(title="IntroducciÃ³n a entrevistas", type="LINK", url="https://example.com/l1",
                            active=True),
        ]
        for m in materials:
            db.add(m)

    db.commit()
    print("Seed completado correctamente.")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


