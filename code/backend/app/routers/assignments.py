"""Router de asignaciones (joven-profesional)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.schemas.assignment import AssignmentCreate
from app.services.assignment_service import (
    assert_user_can_create_assignment,
    assert_user_can_end_assignment,
    assignment_created_payload,
    assignment_ended_payload,
    create_active_assignment,
    finalize_assignment,
    get_assignment_or_404,
)

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.post("")
def create_assignment(
    data: AssignmentCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Asigna un joven a un profesional. Admin o profesional (solo a sí mismo)."""
    assert_user_can_create_assignment(db, user, data.professional_id)
    assignment = create_active_assignment(db, data.youth_id, data.professional_id)
    return assignment_created_payload(assignment)


@router.patch("/{assignment_id}/end")
def end_assignment(
    assignment_id: Annotated[int, Path(ge=1)],
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Finaliza una asignación (status INACTIVO). Profesional asignado o Admin."""
    assignment = get_assignment_or_404(db, assignment_id)
    assert_user_can_end_assignment(db, user, assignment)
    finalize_assignment(db, assignment)
    return assignment_ended_payload(assignment)
