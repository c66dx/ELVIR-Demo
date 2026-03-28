"""Router de resúmenes cualitativos."""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user, get_current_professional
from app.services.session_access import require_session_access
from app.services.interview_summary_service import (
    create_or_update_professional_summary,
    get_summary_for_session_if_access,
    summary_response_dict,
)

router = APIRouter(tags=["summaries"])


class SummaryRequest(BaseModel):
    summary_text: str
    competency_tags: Optional[list[str]] = None


@router.post("/sessions/{session_id}/summary")
def create_or_update_summary(
    session_id: int,
    data: SummaryRequest,
    prof=Depends(get_current_professional),
    db: Session = Depends(get_db),
):
    """Crea o actualiza resumen cualitativo de una sesión. Solo profesional asignado."""
    return create_or_update_professional_summary(
        db,
        session_id,
        prof,
        data.summary_text,
        data.competency_tags,
    )


@router.get("/sessions/{session_id}/summary")
def get_session_summary(
    session_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene resumen cualitativo de una sesión. Requiere acceso a la sesión."""
    require_session_access(db, session_id, user)
    summary = get_summary_for_session_if_access(db, session_id)
    if not summary:
        return None
    return summary_response_dict(summary)
