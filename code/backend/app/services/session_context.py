"""Etiquetas cargo/caso para la UI de simulación."""
from __future__ import annotations

from sqlalchemy.orm import Session as OrmSession

from app.models.case import Case
from app.models.job_role import JobRole
from app.models.simulation_template import SimulationTemplate


def fetch_session_context_labels(db: OrmSession, simulation_template_id: int) -> dict[str, str] | None:
    """Devuelve jobRoleName y caseName, o None si no hay fila."""
    row = (
        db.query(JobRole.name, Case.name)
        .join(SimulationTemplate, SimulationTemplate.job_role_id == JobRole.id)
        .join(Case, SimulationTemplate.case_id == Case.id)
        .filter(SimulationTemplate.id == simulation_template_id)
        .first()
    )
    if not row:
        return None
    job_role_name, case_name = row
    return {"jobRoleName": job_role_name, "caseName": case_name}
