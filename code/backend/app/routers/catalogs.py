"""Router de catálogos: job-roles, cases, simulation-templates."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.schemas.common import CaseResponse, JobRoleResponse, SimulationTemplateResponse
from app.services.catalogs import (
    competencies_catalog_payload,
    competency_levels_catalog_payload,
    get_simulation_template_by_id,
    list_cases_for_catalog,
    list_job_roles_for_catalog,
    list_simulation_templates_for_catalog,
    resolve_simulation_template_default_case,
)

router = APIRouter(tags=["catalogs"])


@router.get("/job-roles", response_model=list[JobRoleResponse])
def list_job_roles(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista cargos/puestos activos. Usado para selector de simulación y prompt dinámico."""
    return list_job_roles_for_catalog(db)


@router.get("/cases", response_model=list[CaseResponse])
def list_cases(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista casos/dificultades activos (Normal, Baja, Media, Alta)."""
    return list_cases_for_catalog(db)


@router.get("/simulation-templates", response_model=list[SimulationTemplateResponse])
def list_simulation_templates(
    job_role_id: Annotated[int | None, Query(ge=1)] = None,
    case_id: Annotated[int | None, Query(ge=1)] = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista plantillas cargo-caso. Filtros opcionales: job_role_id, case_id."""
    return list_simulation_templates_for_catalog(db, job_role_id, case_id)


@router.get("/simulation-templates/resolve", response_model=SimulationTemplateResponse | None)
def resolve_simulation_template(
    job_role_id: Annotated[int, Query(ge=1)],
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resuelve plantilla cuando el usuario elige solo cargo: usa caso NORMAL por defecto."""
    return resolve_simulation_template_default_case(db, job_role_id)


@router.get("/competencies")
def list_competencies(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista catálogo de competencias activas."""
    return competencies_catalog_payload(db)


@router.get("/competency-levels")
def list_competency_levels(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista niveles de competencia (BAJO, MEDIO, ALTO)."""
    return competency_levels_catalog_payload(db)


@router.get("/simulation-templates/{template_id}", response_model=SimulationTemplateResponse | None)
def get_simulation_template(
    template_id: Annotated[int, Path(ge=1)],
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene detalle de una plantilla por ID."""
    return get_simulation_template_by_id(db, template_id)
