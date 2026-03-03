"""Router de sesiones."""
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.session import Session as SessionModel
from app.models.session_event import SessionEvent
from app.models.session_transcript import SessionTranscript
from app.models.user import User
from app.models.youth import Youth
from app.models.professional import Professional
from app.models.assignment import Assignment
from app.models.session_competency import SessionCompetency
from app.models.competency import Competency
from app.models.competency_level import CompetencyLevel
from app.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionCloseRequest,
    SessionStartResponse,
    SessionEventResponse,
    TranscriptResponse,
)
from app.core.dependencies import get_current_user, get_current_professional
from pydantic import BaseModel

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCompetencyItem(BaseModel):
    competency_slug: str
    level_slug: str
    comment: str | None = None


class SessionCompetenciesRequest(BaseModel):
    items: list[SessionCompetencyItem]


def _check_youth_access(db: Session, user: User, youth_id: int) -> bool:
    """Verifica si el usuario tiene permiso para acceder al joven (propio o asignado)."""
    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        return youth and youth.id == youth_id
    if user.role == "PROFESIONAL":
        assign = db.query(Assignment).filter(
            Assignment.youth_id == youth_id,
            Assignment.status == "ACTIVO",
        ).join(Professional, Assignment.professional_id == Professional.id).filter(
            Professional.user_id == user.id,
        ).first()
        return assign is not None
    return False


@router.post("", response_model=SessionResponse)
def create_session(
    data: SessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea una nueva sesión de simulación (status EN_CURSO). Requiere acceso al joven."""
    if not _check_youth_access(db, user, data.youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado al joven")
    session = SessionModel(
        youth_id=data.youth_id,
        professional_id=data.professional_id,
        simulation_template_id=data.simulation_template_id,
        mode=data.mode,
        status="EN_CURSO",
    )
    db.add(session)
    db.flush()
    db.add(SessionEvent(session_id=session.id, event_type="CREATED", payload={"source": "backend"}))
    db.commit()
    db.refresh(session)
    return SessionResponse.model_validate(session)


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    youth_id: int | None = Query(None, description="ID del joven (requerido para profesional)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista sesiones. JOVEN: solo las suyas. PROFESIONAL: de jóvenes asignados o filtro por youth_id."""
    if not youth_id:
        if user.role == "JOVEN":
            youth = db.query(Youth).filter(Youth.user_id == user.id).first()
            youth_id = youth.id if youth else -1
            sessions = db.query(SessionModel).filter(SessionModel.youth_id == youth_id).order_by(SessionModel.started_at.desc()).all()
        else:
            prof = db.query(Professional).filter(Professional.user_id == user.id).first()
            if not prof:
                sessions = []
            else:
                youth_ids = [a[0] for a in db.query(Assignment.youth_id).filter(
                    Assignment.professional_id == prof.id, Assignment.status == "ACTIVO"
                ).all()]
                sessions = (
                    db.query(SessionModel)
                    .filter(SessionModel.youth_id.in_(youth_ids))
                    .order_by(SessionModel.started_at.desc())
                    .all()
                ) if youth_ids else []
    else:
        if not _check_youth_access(db, user, youth_id):
            raise HTTPException(status_code=403, detail="Acceso denegado")
        sessions = db.query(SessionModel).filter(SessionModel.youth_id == youth_id).order_by(SessionModel.started_at.desc()).all()
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get("/{session_id}/context")
def get_session_context(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna jobRoleName y caseName para mostrar en la UI de simulación."""
    from app.models.simulation_template import SimulationTemplate
    from app.models.job_role import JobRole
    from app.models.case import Case
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not _check_youth_access(db, user, session.youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    t = db.query(SimulationTemplate).filter(SimulationTemplate.id == session.simulation_template_id).first()
    if not t:
        return None
    jr = db.query(JobRole).filter(JobRole.id == t.job_role_id).first()
    c = db.query(Case).filter(Case.id == t.case_id).first()
    if not jr or not c:
        return None
    return {"jobRoleName": jr.name, "caseName": c.name}


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene el detalle de una sesión. Requiere acceso al joven de la sesión."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not _check_youth_access(db, user, session.youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return SessionResponse.model_validate(session)


@router.post("/{session_id}/start", response_model=SessionStartResponse)
def start_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Inicia la experiencia con LiveAvatar: PATCH contexto, token, start. Devuelve livekit_url+access_token o embed placeholder."""
    from app.models.simulation_template import SimulationTemplate
    from app.models.job_role import JobRole
    from app.models.case import Case
    from app.config import settings
    from app.services.liveavatar import start_liveavatar_session, LiveAvatarError

    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not _check_youth_access(db, user, session.youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")

    template = db.query(SimulationTemplate).filter(
        SimulationTemplate.id == session.simulation_template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    job_role = db.query(JobRole).filter(JobRole.id == template.job_role_id).first()
    case = db.query(Case).filter(Case.id == template.case_id).first()
    if not job_role or not case:
        raise HTTPException(status_code=404, detail="Cargo o caso no encontrado")

    # Integración LiveAvatar si está configurada
    context_id = settings.LIVEAVATAR_CONTEXT_ID or template.liveavatar_context_id
    if settings.LIVEAVATAR_API_KEY and context_id:
        try:
            result = start_liveavatar_session(job_role, case, template)
            live_id = result.get("session_id") or f"live-{session_id}"
            session.liveavatar_session_id = str(live_id)
            db.add(SessionEvent(
                session_id=session.id,
                event_type="LIVEAVATAR_STARTED",
                payload={"liveavatar_session_id": live_id},
            ))
            db.commit()
            db.refresh(session)
            return SessionStartResponse(
                session_id=session.id,
                liveavatar_session_id=str(live_id),
                livekit_url=result.get("livekit_url"),
                access_token=result.get("access_token"),
            )
        except LiveAvatarError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

    # Placeholder si LiveAvatar no está configurado
    live_id = f"live-{session_id}-{int(datetime.now(timezone.utc).timestamp())}"
    session.liveavatar_session_id = live_id
    db.add(SessionEvent(
        session_id=session.id,
        event_type="LIVEAVATAR_STARTED",
        payload={"liveavatar_session_id": live_id},
    ))
    db.commit()
    db.refresh(session)
    placeholder_url = "data:text/html;charset=utf-8," + quote(
        "<html><body style='display:flex;align-items:center;justify-content:center;height:100%;font-family:sans-serif'><p>Simulación LiveAvatar (configurar LIVEAVATAR_* en .env)</p></body></html>"
    )
    return SessionStartResponse(
        session_id=session.id,
        liveavatar_session_id=live_id,
        embed={"type": "iframe", "url": placeholder_url},
    )


@router.post("/{session_id}/close", response_model=SessionResponse)
def close_session(
    session_id: int,
    data: SessionCloseRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cierra la sesión: actualiza status (COMPLETADA/CANCELADA/ERROR), ended_at, duration y métricas.
    Si tiene liveavatar_session_id, obtiene la transcripción desde LiveAvatar y la persiste."""
    from app.services.liveavatar import get_session_transcript

    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not _check_youth_access(db, user, session.youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    session.status = data.status
    session.ended_at = datetime.now(timezone.utc)
    metrics = dict(data.metrics) if data.metrics else {}
    if data.motivo:
        metrics["motivo"] = data.motivo
    if "duration_seconds" in metrics:
        session.duration_seconds = metrics["duration_seconds"]
    else:
        if session.started_at:
            delta = datetime.now(timezone.utc) - session.started_at
            session.duration_seconds = int(delta.total_seconds())
    session.metrics = metrics if metrics else data.metrics

    # Obtener transcripción desde LiveAvatar si aplica (no bloquea el cierre si falla)
    if session.liveavatar_session_id:
        transcript_data = get_session_transcript(session.liveavatar_session_id)
        if transcript_data:
            existing = db.query(SessionTranscript).filter(SessionTranscript.session_id == session_id).first()
            if existing:
                existing.transcript_data = transcript_data.get("transcript_data", [])
                existing.session_active = transcript_data.get("session_active")
                existing.fetched_at = datetime.now(timezone.utc)
            else:
                db.add(SessionTranscript(
                    session_id=session_id,
                    transcript_data=transcript_data.get("transcript_data", []),
                    session_active=transcript_data.get("session_active"),
                ))

    db.add(SessionEvent(session_id=session.id, event_type="ENDED", payload={"status": data.status}))
    db.commit()
    db.refresh(session)
    return SessionResponse.model_validate(session)


@router.get("/{session_id}/transcript", response_model=TranscriptResponse | None)
def get_session_transcript_endpoint(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene la transcripción de la conversación de una sesión. Requiere acceso a la sesión."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not _check_youth_access(db, user, session.youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    transcript = db.query(SessionTranscript).filter(SessionTranscript.session_id == session_id).first()
    if not transcript:
        return None
    return TranscriptResponse(
        transcript_data=transcript.transcript_data,
        session_active=transcript.session_active,
        fetched_at=transcript.fetched_at,
    )


@router.get("/{session_id}/events", response_model=list[SessionEventResponse])
def list_session_events(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista eventos de trazabilidad de una sesión (CREATED, LIVEAVATAR_STARTED, ENDED, etc.)."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not _check_youth_access(db, user, session.youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    events = db.query(SessionEvent).filter(SessionEvent.session_id == session_id).order_by(SessionEvent.occurred_at).all()
    return [SessionEventResponse.model_validate(e) for e in events]


@router.post("/{session_id}/competencies")
def create_or_update_session_competencies(
    session_id: int,
    data: SessionCompetenciesRequest,
    prof=Depends(get_current_professional),
    db: Session = Depends(get_db),
):
    """Registra o actualiza evaluación por competencias de una sesión. Solo profesional asignado."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    assign = db.query(Assignment).filter(
        Assignment.youth_id == session.youth_id,
        Assignment.professional_id == prof.id,
        Assignment.status == "ACTIVO",
    ).first()
    if not assign:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    # Eliminar evaluaciones previas para reemplazar
    db.query(SessionCompetency).filter(SessionCompetency.session_id == session_id).delete()
    for item in data.items:
        comp = db.query(Competency).filter(Competency.slug == item.competency_slug, Competency.is_active == True).first()
        level = db.query(CompetencyLevel).filter(CompetencyLevel.slug == item.level_slug).first()
        if not comp or not level:
            raise HTTPException(status_code=400, detail=f"Competencia '{item.competency_slug}' o nivel '{item.level_slug}' no encontrado")
        db.add(SessionCompetency(
            session_id=session_id,
            competency_id=comp.id,
            level_id=level.id,
            comment=item.comment,
        ))
    db.commit()
    return {"session_id": session_id, "items_count": len(data.items)}


@router.get("/{session_id}/competencies")
def get_session_competencies(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene evaluación por competencias de una sesión. Requiere acceso a la sesión."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not _check_youth_access(db, user, session.youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    items = db.query(SessionCompetency).filter(SessionCompetency.session_id == session_id).all()
    result = []
    for sc in items:
        comp = db.query(Competency).filter(Competency.id == sc.competency_id).first()
        level = db.query(CompetencyLevel).filter(CompetencyLevel.id == sc.level_id).first()
        if comp and level:
            result.append({
                "competency": {"slug": comp.slug, "name": comp.name},
                "level": {"slug": level.slug, "label": level.label},
                "comment": sc.comment,
            })
    return {"session_id": session_id, "items": result}
