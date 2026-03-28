"""Router de sesiones."""
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File, Form, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionCloseRequest,
    SessionStartResponse,
    SessionEventResponse,
    TranscriptResponse,
    SessionStatsResponse,
    SessionEvaluationRequest,
    SessionCompetenciesRequest,
    SessionEventCreate,
)
from app.services.session_access import (
    expire_stale_sessions,
    require_session_access,
    require_session_for_start,
    touch_session_heartbeat,
)
from app.services.session_events import list_session_events_ordered, persist_manual_session_event
from app.services.session_list import apply_sessions_pagination_headers, fetch_sessions_list
from app.services.session_stats import compute_session_stats
from app.services.session_close import apply_close_session
from app.services.session_start import apply_start_session
from app.services.session_audio import get_session_audio_record, upload_session_audio_for_user
from app.services.session_transcript import get_transcript_response
from app.services.session_create import create_session_record
from app.services.session_context import fetch_session_context_labels
from app.services.session_evaluation import persist_liveavatar_evaluation
from app.services.session_competencies import (
    build_session_competencies_payload,
    replace_session_competencies,
)
from app.schemas.session_audio import SessionAudioResponse
from app.core.dependencies import get_current_user, get_current_professional
from app.config import settings
router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
def create_session(
    data: SessionCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea una nueva sesión de simulación (status EN_CURSO). Requiere acceso al joven."""
    request_id = getattr(request.state, "request_id", "unknown")
    session = create_session_record(db, user, data, request_id)
    return SessionResponse.model_validate(session)


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    youth_id: int | None = Query(None, description="ID del joven (requerido para profesional)"),
    search: str | None = Query(None, description="Búsqueda por nombre o RUT del joven"),
    status: str | None = Query(None, description="Estado de la sesión"),
    mode: str | None = Query(None, description="Modo de la sesión"),
    start_date: date | None = Query(None, description="Fecha inicio desde (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="Fecha inicio hasta (YYYY-MM-DD)"),
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    response: Response = None,
):
    """Lista sesiones. JOVEN: solo las suyas. PROFESIONAL: de jóvenes asignados o filtro por youth_id."""
    items, pag = fetch_sessions_list(
        db,
        user,
        youth_id,
        search=search,
        status=status,
        mode=mode,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    apply_sessions_pagination_headers(response, pag)
    return [SessionResponse.model_validate(s) for s in items]


@router.get("/stats", response_model=SessionStatsResponse)
def get_session_stats(
    youth_id: int | None = Query(None),
    months: int = Query(6, ge=1, le=24),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resumen de sesiones (conteos por estado y curva mensual de completadas)."""
    return compute_session_stats(db, user, youth_id, months)


@router.get("/{session_id}/context")
def get_session_context(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna jobRoleName y caseName para mostrar en la UI de simulación."""
    session = require_session_access(db, session_id, user)
    return fetch_session_context_labels(db, session.simulation_template_id)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene el detalle de una sesión. Requiere acceso al joven de la sesión."""
    expire_stale_sessions(db)
    session = require_session_access(db, session_id, user)
    return SessionResponse.model_validate(session)


@router.post("/{session_id}/heartbeat")
def heartbeat_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualiza last_heartbeat_at de una sesión en curso."""
    return touch_session_heartbeat(db, session_id, user)


@router.post("/{session_id}/start", response_model=SessionStartResponse)
def start_session(
    session_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Inicia la experiencia con LiveAvatar: PATCH contexto, token, start. Devuelve livekit_url+access_token o embed de respaldo."""
    request_id = getattr(request.state, "request_id", "unknown")

    expire_stale_sessions(db)
    session = require_session_for_start(db, session_id, user)
    session.last_heartbeat_at = datetime.now(timezone.utc)

    return apply_start_session(db, session, session_id, request_id)


@router.post("/{session_id}/close", response_model=SessionResponse)
def close_session(
    session_id: int,
    data: SessionCloseRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cierra la sesión: actualiza status (COMPLETADA/CANCELADA/ERROR), ended_at, duration y métricas.
    Si tiene liveavatar_session_id, obtiene la transcripción desde LiveAvatar y la persiste."""
    session = require_session_access(db, session_id, user)
    request_id = getattr(request.state, "request_id", "unknown")
    apply_close_session(db, session, data, request_id)
    return SessionResponse.model_validate(session)


@router.post("/evaluation")
def receive_session_evaluation(
    data: SessionEvaluationRequest,
    request: Request,
    db: Session = Depends(get_db),
    webhook_secret: str | None = Header(None, alias="X-ELVIR-Webhook-Secret"),
):
    """Recibe evaluación externa (ej. LiveAvatar) y la guarda en session.metrics."""
    if settings.LIVEAVATAR_WEBHOOK_SECRET:
        if not webhook_secret or webhook_secret != settings.LIVEAVATAR_WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="Webhook no autorizado")

    request_id = getattr(request.state, "request_id", "unknown")
    session_id = persist_liveavatar_evaluation(db, data, request_id)
    return {"ok": True, "session_id": session_id}


@router.get("/{session_id}/transcript", response_model=TranscriptResponse | None)
def get_session_transcript_endpoint(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene la transcripción de la conversación de una sesión. Requiere acceso a la sesión."""
    require_session_access(db, session_id, user)
    return get_transcript_response(db, session_id)


@router.post("/{session_id}/audio", response_model=SessionAudioResponse)
def upload_session_audio(
    session_id: int,
    request: Request,
    file: UploadFile = File(...),
    duration_seconds: int | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sube el audio grabado de una sesión. Joven o profesional asignado."""
    base = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    row = upload_session_audio_for_user(db, session_id, user, file, duration_seconds, base)
    return SessionAudioResponse.model_validate(row)


@router.get("/{session_id}/audio", response_model=SessionAudioResponse | None)
def get_session_audio(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene metadata del audio de una sesión. Requiere acceso a la sesión."""
    require_session_access(db, session_id, user)
    audio = get_session_audio_record(db, session_id)
    if not audio:
        return None
    return SessionAudioResponse.model_validate(audio)


@router.get("/{session_id}/events", response_model=list[SessionEventResponse])
def list_session_events(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista eventos de trazabilidad de una sesión (CREATED, LIVEAVATAR_STARTED, ENDED, etc.)."""
    require_session_access(db, session_id, user)
    events = list_session_events_ordered(db, session_id)
    return [SessionEventResponse.model_validate(e) for e in events]


@router.post("/{session_id}/events", response_model=SessionEventResponse)
def create_session_event(
    session_id: int,
    data: SessionEventCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Registra evento manual para una sesión. Requiere acceso a la sesión."""
    require_session_access(db, session_id, user)
    request_id = getattr(request.state, "request_id", None)
    event = persist_manual_session_event(db, session_id, data, request_id)
    return SessionEventResponse.model_validate(event)


@router.post("/{session_id}/competencies")
def create_or_update_session_competencies(
    session_id: int,
    data: SessionCompetenciesRequest,
    prof=Depends(get_current_professional),
    db: Session = Depends(get_db),
):
    """Registra o actualiza evaluación por competencias de una sesión. Solo profesional asignado."""
    return replace_session_competencies(db, session_id, prof, data)


@router.get("/{session_id}/competencies")
def get_session_competencies(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene evaluación por competencias de una sesión. Requiere acceso a la sesión."""
    require_session_access(db, session_id, user)
    return build_session_competencies_payload(db, session_id)

