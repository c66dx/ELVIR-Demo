"""Router de catálogos: job-roles, cases, simulation-templates."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job_role import JobRole
from app.models.case import Case
from app.models.simulation_template import SimulationTemplate
from app.models.competency import Competency
from app.models.competency_level import CompetencyLevel
from app.schemas.common import JobRoleResponse, CaseResponse, SimulationTemplateResponse, JobRoleRef, CaseRef
from app.core.dependencies import get_current_user

router = APIRouter(tags=["catalogs"])


def _parse_competencias(val) -> Optional[list]:
    """Parsea competencias desde JSON string o lista."""
    if val is None:
        return None
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val) if val.startswith("[") else [val]
        except json.JSONDecodeError:
            return [val]
    return None


@router.get("/job-roles", response_model=list[JobRoleResponse])
def list_job_roles(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista cargos/puestos activos. Usado para selector de simulación y prompt dinámico."""
    roles = db.query(JobRole).filter(JobRole.is_active == True).all()
    return [
        JobRoleResponse(
            id=r.id,
            slug=r.slug,
            name=r.name,
            description=r.description,
            objetivo=r.objetivo,
            competencias=_parse_competencias(r.competencias),
            is_active=r.is_active,
        )
        for r in roles
    ]


@router.get("/cases", response_model=list[CaseResponse])
def list_cases(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista casos/dificultades activos (Normal, Baja, Media, Alta)."""
    cases = db.query(Case).filter(Case.is_active == True).all()
    return [CaseResponse.model_validate(c) for c in cases]


@router.get("/simulation-templates", response_model=list[SimulationTemplateResponse])
def list_simulation_templates(
    job_role_id: Optional[int] = Query(None),
    case_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista plantillas cargo×caso. Filtros opcionales: job_role_id, case_id."""
    q = db.query(SimulationTemplate).filter(SimulationTemplate.is_active == True)
    if job_role_id:
        q = q.filter(SimulationTemplate.job_role_id == job_role_id)
    if case_id:
        q = q.filter(SimulationTemplate.case_id == case_id)
    templates = q.all()
    result = []
    for t in templates:
        jr = db.query(JobRole).filter(JobRole.id == t.job_role_id).first()
        c = db.query(Case).filter(Case.id == t.case_id).first()
        result.append(
            SimulationTemplateResponse(
                id=t.id,
                job_role=JobRoleRef(id=jr.id, slug=jr.slug, name=jr.name),
                case=CaseRef(id=c.id, slug=c.slug, difficulty=c.difficulty, name=c.name),
                liveavatar_context_id=t.liveavatar_context_id,
                liveavatar_avatar_id=t.liveavatar_avatar_id,
                liveavatar_voice_id=t.liveavatar_voice_id,
                is_active=t.is_active,
            )
        )
    return result


@router.get("/simulation-templates/resolve", response_model=Optional[SimulationTemplateResponse])
def resolve_simulation_template(
    job_role_id: int = Query(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resuelve plantilla cuando el usuario elige solo cargo: usa caso NORMAL por defecto."""
    normal_case = db.query(Case).filter(Case.difficulty == "NORMAL", Case.is_active == True).first()
    if not normal_case:
        return None
    t = db.query(SimulationTemplate).filter(
        SimulationTemplate.job_role_id == job_role_id,
        SimulationTemplate.case_id == normal_case.id,
        SimulationTemplate.is_active == True,
    ).first()
    if not t:
        return None
    jr = db.query(JobRole).filter(JobRole.id == t.job_role_id).first()
    c = db.query(Case).filter(Case.id == t.case_id).first()
    return SimulationTemplateResponse(
        id=t.id,
        job_role=JobRoleRef(id=jr.id, slug=jr.slug, name=jr.name),
        case=CaseRef(id=c.id, slug=c.slug, difficulty=c.difficulty, name=c.name),
        liveavatar_context_id=t.liveavatar_context_id,
        liveavatar_avatar_id=t.liveavatar_avatar_id,
        liveavatar_voice_id=t.liveavatar_voice_id,
        is_active=t.is_active,
        resolution_reason="DEFAULT_CASE",
    )


@router.get("/competencies")
def list_competencies(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista catálogo de competencias activas."""
    items = db.query(Competency).filter(Competency.is_active == True).order_by(Competency.slug).all()
    return [{"id": c.id, "slug": c.slug, "name": c.name, "is_active": c.is_active} for c in items]


@router.get("/competency-levels")
def list_competency_levels(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista niveles de competencia (BAJO, MEDIO, ALTO)."""
    items = db.query(CompetencyLevel).order_by(CompetencyLevel.sort_order).all()
    return [{"id": l.id, "slug": l.slug, "label": l.label, "sort_order": l.sort_order} for l in items]


@router.get("/simulation-templates/{template_id}", response_model=Optional[SimulationTemplateResponse])
def get_simulation_template(
    template_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene detalle de una plantilla por ID."""
    t = db.query(SimulationTemplate).filter(SimulationTemplate.id == template_id).first()
    if not t:
        return None
    jr = db.query(JobRole).filter(JobRole.id == t.job_role_id).first()
    c = db.query(Case).filter(Case.id == t.case_id).first()
    return SimulationTemplateResponse(
        id=t.id,
        job_role=JobRoleRef(id=jr.id, slug=jr.slug, name=jr.name),
        case=CaseRef(id=c.id, slug=c.slug, difficulty=c.difficulty, name=c.name),
        liveavatar_context_id=t.liveavatar_context_id,
        liveavatar_avatar_id=t.liveavatar_avatar_id,
        liveavatar_voice_id=t.liveavatar_voice_id,
        is_active=t.is_active,
    )
