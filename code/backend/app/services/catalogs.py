"""Consultas y armado de respuestas de catálogos (job-roles, cases, plantillas, competencias)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session as OrmSession

from app.models.case import Case
from app.models.competency import Competency
from app.models.competency_level import CompetencyLevel
from app.models.job_role import JobRole
from app.models.simulation_template import SimulationTemplate
from app.schemas.common import (
    CaseRef,
    CaseResponse,
    JobRoleRef,
    JobRoleResponse,
    SimulationTemplateResponse,
)


def parse_competencias(val: Any) -> list | None:
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


def simulation_template_to_response(
    t: SimulationTemplate,
    jr: JobRole,
    c: Case,
    *,
    resolution_reason: str | None = None,
) -> SimulationTemplateResponse:
    return SimulationTemplateResponse(
        id=t.id,
        job_role=JobRoleRef(id=jr.id, slug=jr.slug, name=jr.name),
        case=CaseRef(id=c.id, slug=c.slug, difficulty=c.difficulty, name=c.name),
        liveavatar_context_id=t.liveavatar_context_id,
        liveavatar_avatar_id=t.liveavatar_avatar_id,
        liveavatar_voice_id=t.liveavatar_voice_id,
        is_active=t.is_active,
        resolution_reason=resolution_reason,
    )


def list_job_roles_for_catalog(db: OrmSession) -> list[JobRoleResponse]:
    roles = db.query(JobRole).filter(JobRole.is_active == True).all()
    return [
        JobRoleResponse(
            id=r.id,
            slug=r.slug,
            name=r.name,
            description=r.description,
            objetivo=r.objetivo,
            competencias=parse_competencias(r.competencias),
            is_active=r.is_active,
        )
        for r in roles
    ]


def list_cases_for_catalog(db: OrmSession) -> list[CaseResponse]:
    cases = db.query(Case).filter(Case.is_active == True).all()
    return [CaseResponse.model_validate(c) for c in cases]


def list_simulation_templates_for_catalog(
    db: OrmSession,
    job_role_id: int | None,
    case_id: int | None,
) -> list[SimulationTemplateResponse]:
    q = (
        db.query(SimulationTemplate, JobRole, Case)
        .join(JobRole, SimulationTemplate.job_role_id == JobRole.id)
        .join(Case, SimulationTemplate.case_id == Case.id)
        .filter(SimulationTemplate.is_active == True)
    )
    if job_role_id:
        q = q.filter(SimulationTemplate.job_role_id == job_role_id)
    if case_id:
        q = q.filter(SimulationTemplate.case_id == case_id)
    rows = q.all()
    return [simulation_template_to_response(t, jr, c) for t, jr, c in rows]


def resolve_simulation_template_default_case(
    db: OrmSession,
    job_role_id: int,
) -> SimulationTemplateResponse | None:
    row = (
        db.query(SimulationTemplate, JobRole, Case)
        .join(JobRole, SimulationTemplate.job_role_id == JobRole.id)
        .join(Case, SimulationTemplate.case_id == Case.id)
        .filter(
            SimulationTemplate.job_role_id == job_role_id,
            SimulationTemplate.is_active == True,
            Case.difficulty == "NORMAL",
            Case.is_active == True,
        )
        .first()
    )
    if not row:
        return None
    t, jr, c = row
    return simulation_template_to_response(t, jr, c, resolution_reason="DEFAULT_CASE")


def get_simulation_template_by_id(
    db: OrmSession,
    template_id: int,
) -> SimulationTemplateResponse | None:
    row = (
        db.query(SimulationTemplate, JobRole, Case)
        .join(JobRole, SimulationTemplate.job_role_id == JobRole.id)
        .join(Case, SimulationTemplate.case_id == Case.id)
        .filter(SimulationTemplate.id == template_id)
        .first()
    )
    if not row:
        return None
    t, jr, c = row
    return simulation_template_to_response(t, jr, c)


def competencies_catalog_payload(db: OrmSession) -> list[dict]:
    items = db.query(Competency).filter(Competency.is_active == True).order_by(Competency.slug).all()
    return [{"id": c.id, "slug": c.slug, "name": c.name, "is_active": c.is_active} for c in items]


def competency_levels_catalog_payload(db: OrmSession) -> list[dict]:
    items = db.query(CompetencyLevel).order_by(CompetencyLevel.sort_order).all()
    return [{"id": l.id, "slug": l.slug, "label": l.label, "sort_order": l.sort_order} for l in items]
