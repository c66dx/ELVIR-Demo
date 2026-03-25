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


def _fix_mojibake(text: str | None) -> str | None:
    if not text:
        return text
    if "Ã" in text or "Â" in text:
        try:
            return text.encode("latin1").decode("utf-8")
        except UnicodeDecodeError:
            return text
    return text


def _get_or_create_user(db: Session, email: str, role: str, is_active: bool = True) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, password_hash=get_password_hash("test123"), role=role, is_active=is_active)
        db.add(user)
        db.flush()
    return user


def _get_or_create_professional(db: Session, user: User | None, display_name: str) -> Professional | None:
    if not user:
        return None
    prof = db.query(Professional).filter(Professional.user_id == user.id).first()
    if not prof:
        prof = Professional(user_id=user.id, display_name=display_name, is_active=True)
        db.add(prof)
        db.flush()
    return prof


def _get_or_create_youth(
    db: Session,
    *,
    user: User | None,
    identifier: str | None,
    display_name: str,
    login_enabled: bool,
    phone: str | None = None,
    general_notes: str | None = None,
) -> Youth:
    youth = None
    if user:
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
    if not youth and identifier:
        youth = db.query(Youth).filter(Youth.identifier == identifier).first()
    if not youth:
        youth = Youth(
            user_id=user.id if user else None,
            login_enabled=login_enabled,
            display_name=display_name,
            identifier=identifier,
            phone=phone,
            is_active=True,
            general_notes=general_notes,
        )
        db.add(youth)
        db.flush()
    return youth


def _ensure_assignment(db: Session, youth: Youth | None, prof: Professional | None) -> None:
    if not youth or not prof:
        return
    active = (
        db.query(Assignment)
        .filter(Assignment.youth_id == youth.id, Assignment.status == "ACTIVO")
        .order_by(Assignment.assigned_at.desc())
        .first()
    )
    if active:
        return
    db.add(Assignment(youth_id=youth.id, professional_id=prof.id, status="ACTIVO"))


def seed(db: Session):
    """Ejecuta la carga inicial."""
    # Usuarios (misma convención que preview: Gmail para jóvenes, @test.cl tutor/admin)
    if db.query(User).count() == 0:
        users = [
            User(email="elvir.demo+joven1@gmail.com", password_hash=get_password_hash("test123"), role="JOVEN", is_active=True),
            User(email="elvir.demo+joven2@gmail.com", password_hash=get_password_hash("test123"), role="JOVEN", is_active=True),
            User(email="elvir.demo+joven3@gmail.com", password_hash=get_password_hash("test123"), role="JOVEN", is_active=True),
            User(email="elvir.demo+joven4@gmail.com", password_hash=get_password_hash("test123"), role="JOVEN", is_active=True),
            User(email="elvir.demo+joven5@gmail.com", password_hash=get_password_hash("test123"), role="JOVEN", is_active=True),
            User(email="elvir.demo+joven6@gmail.com", password_hash=get_password_hash("test123"), role="JOVEN", is_active=True),
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

    # Jóvenes
    if db.query(Youth).count() == 0:
        u1 = db.query(User).filter(User.email == "elvir.demo+joven1@gmail.com").first()
        u2 = db.query(User).filter(User.email == "elvir.demo+joven2@gmail.com").first()
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

    # Asegurar seeds y asignaciones aunque la BD ya tenga datos
    seed_joven1 = _get_or_create_user(db, "elvir.demo+joven1@gmail.com", "JOVEN", is_active=True)
    seed_joven2 = _get_or_create_user(db, "elvir.demo+joven2@gmail.com", "JOVEN", is_active=True)
    seed_joven3 = _get_or_create_user(db, "elvir.demo+joven3@gmail.com", "JOVEN", is_active=True)
    seed_joven4 = _get_or_create_user(db, "elvir.demo+joven4@gmail.com", "JOVEN", is_active=True)
    seed_joven5 = _get_or_create_user(db, "elvir.demo+joven5@gmail.com", "JOVEN", is_active=True)
    seed_joven6 = _get_or_create_user(db, "elvir.demo+joven6@gmail.com", "JOVEN", is_active=True)
    seed_prof_user = _get_or_create_user(db, "prof@test.cl", "PROFESIONAL", is_active=True)
    _get_or_create_user(db, "admin@test.cl", "ADMIN", is_active=True)

    seed_prof = _get_or_create_professional(db, seed_prof_user, "Profesional Test")
    y1 = _get_or_create_youth(
        db,
        user=seed_joven1,
        identifier="JOV-001",
        display_name="María González",
        login_enabled=True,
        phone="+56912345678",
        general_notes="Notas generales",
    )
    y2 = _get_or_create_youth(
        db,
        user=seed_joven2,
        identifier="JOV-002",
        display_name="Juan Rodríguez",
        login_enabled=False,
    )
    y3 = _get_or_create_youth(
        db,
        user=None,
        identifier="JOV-003",
        display_name="Carolina Flores",
        login_enabled=True,
    )
    y4 = _get_or_create_youth(
        db,
        user=None,
        identifier="JOV-004",
        display_name="Roberto Díaz",
        login_enabled=True,
    )
    y5 = _get_or_create_youth(
        db,
        user=seed_joven3,
        identifier="JOV-005",
        display_name="Valentina Rojas",
        login_enabled=True,
        phone="+56955550101",
        general_notes="Se recomienda retroalimentación concreta y breve.",
    )
    y6 = _get_or_create_youth(
        db,
        user=seed_joven4,
        identifier="JOV-006",
        display_name="Camilo Pérez",
        login_enabled=True,
        phone="+56955550102",
        general_notes="Prefiere preguntas directas y ejemplos prácticos.",
    )
    y7 = _get_or_create_youth(
        db,
        user=seed_joven5,
        identifier="JOV-007",
        display_name="Francisca Soto",
        login_enabled=True,
        phone="+56955550103",
        general_notes="Mejora con apoyo visual y lenguaje sencillo.",
    )
    y8 = _get_or_create_youth(
        db,
        user=seed_joven6,
        identifier="JOV-008",
        display_name="Diego Muñoz",
        login_enabled=True,
        phone="+56955550104",
        general_notes="Necesita contraste alto y textos grandes.",
    )
    for y in (y1, y2, y3, y4, y5, y6, y7, y8):
        _ensure_assignment(db, y, seed_prof)
# Cargos (contenido de Catalina - cargos.json + Context Dinamico roles-data)
    if db.query(JobRole).count() == 0:
        roles = [
            JobRole(slug="operario", name="Operario",
                    description="El cargo de Operario está orientado a la realización de tareas operativas básicas dentro de la organización, siguiendo instrucciones y procedimientos definidos. El rol requiere responsabilidad, cumplimiento de normas y capacidad para trabajar de manera organizada y colaborativa.",
                    objetivo="Ejecutar tareas operativas conforme a procedimientos establecidos, asegurando eficiencia, seguridad y calidad en los procesos productivos o de servicio.",
                    competencias=json.dumps(["Responsabilidad", "Trabajo en equipo", "Cumplimiento de normas y procedimientos", "Gestión del tiempo", "Atención al detalle"]),
                    is_active=True),
            JobRole(slug="atencion-publico", name="Atención de Público",
                    description="El cargo de Atención de Público tiene como objetivo atender y orientar a personas usuarias o clientes, brindando respuestas claras y oportunas según los lineamientos establecidos. El rol demanda habilidades de comunicación, trato cordial y adecuada gestión de situaciones diversas.",
                    objetivo="Atender y orientar a clientes o usuarios, gestionando consultas, reclamos y solicitudes de manera eficiente y cordial, contribuyendo a una experiencia de servicio de calidad.",
                    competencias=json.dumps(["Comunicación efectiva", "Empatía", "Orientación al cliente", "Resolución de conflictos", "Manejo del estrés"]),
                    is_active=True),
            JobRole(slug="administrativo", name="Administrativo",
                    description="El cargo Administrativo se enfoca en apoyar la gestión interna de la organización mediante la ejecución de tareas administrativas y de apoyo documental. El rol requiere organización, orden, cumplimiento de procedimientos y manejo básico de herramientas de oficina.",
                    objetivo="Gestionar y ejecutar procesos administrativos y documentales, brindando soporte operativo a las distintas áreas de la organización.",
                    competencias=json.dumps(["Organización", "Gestión documental", "Comunicación formal", "Planificación", "Atención al detalle"]),
                    is_active=True),
            JobRole(slug="tecnico-profesional", name="Técnico-Profesional",
                    description="El cargo Técnico Profesional está orientado al desarrollo de funciones técnicas o especializadas dentro de un área específica. El rol implica aplicar conocimientos profesionales, cumplir estándares definidos y aportar al correcto funcionamiento de los procesos del área.",
                    objetivo="Desarrollar funciones técnicas especializadas, aplicando conocimientos profesionales para resolver problemas operativos y asegurar el cumplimiento de estándares técnicos y normativos.",
                    competencias=json.dumps(["Pensamiento analítico", "Resolución de problemas técnicos", "Autonomía", "Responsabilidad profesional", "Mejora continua"]),
                    is_active=True),
        ]
        for r in roles:
            db.add(r)
        db.flush()
# Casos (contenido de Catalina - indicaciones.json, mapeo: baja->apoyo_regulacion, media->alta_estructuracion, alta->exigencia_alta)
    if db.query(Case).count() == 0:
        cases = [
            Case(slug="normal", name="Entrevista Normal", difficulty="NORMAL",
                 prompt_instructions="Realiza preguntas abiertas y complejas. Invita a profundizar y a reflexionar, manteniendo el foco en el mensaje central. Mantén un estilo de entrevista normal. Introduce referencias a la discapacidad de manera acotada. Refuerza las respuestas adecuadas y ayuda a reformular cuando la presentación pierde foco o impacto.",
                 is_active=True),
            Case(slug="baja", name="Dificultad Baja (empático)", difficulty="BAJA",
                 prompt_instructions="Adopta un tono muy acogedor y contenedor. Valida explícitamente cómo se puede estar sintiendo la persona. Realiza preguntas muy simples y concretas. Da tiempo suficiente para responder y ofrece pausas. Refuerza cualquier intento de respuesta. Prioriza la sensación de seguridad y contención por sobre el contenido de la entrevista.",
                 is_active=True),
            Case(slug="media", name="Dificultad Media (guiada)", difficulty="MEDIA",
                 prompt_instructions="Formula preguntas muy guiadas y acotadas. Repite o reformula la pregunta si es necesario. Ayuda explícitamente a ordenar la respuesta, indicando qué tipo de información se espera. Mantén un estilo de entrevista normal. Introduce referencias a la discapacidad de manera acotada. Refuerza las respuestas adecuadas y ayuda a reformular cuando la presentación pierde foco o impacto.",
                 is_active=True),
            Case(slug="alta", name="Dificultad Alta (poco empático)", difficulty="ALTA",
                 prompt_instructions="Realiza preguntas abiertas y complejas. Invita a profundizar y a reflexionar, manteniendo el foco en el mensaje central. Utiliza un estilo de entrevista realista. Introduce preguntas o comentarios directos y poco empáticos sobre la discapacidad cuando corresponda y evalúa la capacidad de sostener una presentación estratégica sin intervenir. Debes ser poco empático, muy serio y con poco tino.",
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
            Competency(slug="comunicacion", name="Comunicación", is_active=True),
            Competency(slug="regulacion_emocional", name="Regulación emocional", is_active=True),
            Competency(slug="trabajo_equipo", name="Trabajo en equipo", is_active=True),
            Competency(slug="organizacion", name="Organización", is_active=True),
            Competency(slug="autonomia", name="Autonomía", is_active=True),
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

    # Reparar textos con encoding incorrecto en materiales existentes
    for material in db.query(SupportMaterial).all():
        new_title = _fix_mojibake(material.title)
        new_description = _fix_mojibake(material.description)
        if new_title != material.title:
            material.title = new_title
        if new_description != material.description:
            material.description = new_description

    # Reparar textos con encoding incorrecto en tablas principales
    for youth in db.query(Youth).all():
        new_name = _fix_mojibake(youth.display_name)
        if new_name != youth.display_name:
            youth.display_name = new_name

    for role in db.query(JobRole).all():
        new_name = _fix_mojibake(role.name)
        new_desc = _fix_mojibake(role.description)
        new_obj = _fix_mojibake(role.objetivo)
        new_comp = _fix_mojibake(role.competencias)
        if new_name != role.name:
            role.name = new_name
        if new_desc != role.description:
            role.description = new_desc
        if new_obj != role.objetivo:
            role.objetivo = new_obj
        if new_comp != role.competencias:
            role.competencias = new_comp

    for case in db.query(Case).all():
        new_name = _fix_mojibake(case.name)
        new_prompt = _fix_mojibake(case.prompt_instructions)
        if new_name != case.name:
            case.name = new_name
        if new_prompt != case.prompt_instructions:
            case.prompt_instructions = new_prompt

    for comp in db.query(Competency).all():
        new_name = _fix_mojibake(comp.name)
        if new_name != comp.name:
            comp.name = new_name

    db.commit()
    print("Seed completado correctamente.")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


