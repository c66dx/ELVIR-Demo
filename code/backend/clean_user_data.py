#!/usr/bin/env python3
"""
Limpia los datos creados por el usuario durante pruebas.
Mantiene los datos del seed (usuarios test, jóvenes, cargos, casos, plantillas).

Elimina:
- Sesiones de simulación (y sus eventos y resúmenes)
- Material de apoyo creado por ti (y sugerencias/vistas asociadas)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.session_event import SessionEvent
from app.models.interview_summary import InterviewSummary
from app.models.session import Session as SessionModel
from app.models.material_view import MaterialView
from app.models.material_suggestion import MaterialSuggestion
from app.models.support_material import SupportMaterial


def clean(db: Session):
    """Elimina datos creados por el usuario, respetando el orden de FK."""
    # 1. Eventos de sesión (referencian sessions)
    deleted_events = db.query(SessionEvent).delete()
    # 2. Resúmenes de entrevista (referencian sessions)
    deleted_summaries = db.query(InterviewSummary).delete()
    # 3. Sesiones
    deleted_sessions = db.query(SessionModel).delete()
    # 4. Vistas de material (referencian youths y support_material)
    deleted_views = db.query(MaterialView).delete()
    # 5. Sugerencias de material (referencian youths y support_material)
    deleted_suggestions = db.query(MaterialSuggestion).delete()
    # 6. Material de apoyo (todos; el seed los vuelve a crear)
    deleted_materials = db.query(SupportMaterial).delete()

    db.commit()

    print("Limpieza completada:")
    print(f"  - {deleted_events} eventos de sesión")
    print(f"  - {deleted_summaries} resúmenes de entrevista")
    print(f"  - {deleted_sessions} sesiones")
    print(f"  - {deleted_views} vistas de material")
    print(f"  - {deleted_suggestions} sugerencias de material")
    print(f"  - {deleted_materials} materiales de apoyo")


def reseed_material(db: Session):
    """Vuelve a crear los 4 materiales del seed."""
    from app.models.job_role import JobRole
    from app.models.case import Case

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
    print(f"  - 4 materiales de apoyo (seed)")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        clean(db)
        reseed_material(db)
        print("\nDatos de prueba (usuarios, jóvenes, cargos, casos) se mantienen.")
    finally:
        db.close()
