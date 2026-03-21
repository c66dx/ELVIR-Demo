"""Router de sesiones."""
import logging
import uuid
import re
from pathlib import Path
from datetime import datetime, date, time, timezone
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File, Form, Header
from sqlalchemy import case, func, select, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.session import Session as SessionModel
from app.models.session_event import SessionEvent
from app.models.session_transcript import SessionTranscript
from app.models.session_audio import SessionAudio
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
from app.schemas.prompt import PromptInput, EvaluationInput
from app.services.prompt_engine import evaluate, PromptProviderError
from app.schemas.session_audio import SessionAudioResponse
from app.core.dependencies import get_current_user, get_current_professional
from app.config import settings
from pydantic import BaseModel
from app.services.notifications import upsert_youth_notification

router = APIRouter(prefix="/sessions", tags=["sessions"])
logger = logging.getLogger("elvir.api")

SESSION_AUDIO_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "audio"
SESSION_AUDIO_EXTENSIONS = {".webm", ".ogg", ".wav", ".mp3", ".m4a"}
SESSION_AUDIO_MAX_MB = 30
SESSION_AUDIO_MAX_BYTES = SESSION_AUDIO_MAX_MB * 1024 * 1024
SESSION_AUDIO_CHUNK_SIZE = 1024 * 1024


def _ensure_session_audio_dir() -> None:
    SESSION_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _save_audio_stream(file: UploadFile, destination: Path) -> int:
    """Guarda audio por chunks y retorna tamaño total escrito."""
    total_written = 0
    with destination.open("wb") as out:
        while True:
            chunk = file.file.read(SESSION_AUDIO_CHUNK_SIZE)
            if not chunk:
                break
            total_written += len(chunk)
            if total_written > SESSION_AUDIO_MAX_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Audio demasiado grande. Máximo: {SESSION_AUDIO_MAX_MB} MB",
                )
            out.write(chunk)
    return total_written


def _transcript_to_text(transcript_data: list[dict] | None) -> str:
    """Convierte transcript_data (lista de turnos) a texto plano."""
    lines: list[str] = []
    for item in transcript_data or []:
        role = (item.get("role") or "speaker").strip()
        text = (item.get("transcript") or "").strip()
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines).strip()


class SessionCompetencyItem(BaseModel):
    competency_slug: str
    level_slug: str
    comment: str | None = None


class SessionCompetenciesRequest(BaseModel):
    items: list[SessionCompetencyItem]


class SessionEvaluationRequest(BaseModel):
    session_id: int | None = None
    liveavatar_session_id: str | None = None
    evaluation: Any
    source: str | None = None


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


def _build_sessions_query(db: Session, user: User, youth_id: int | None):
    """Construye query base de sesiones según rol y filtros de acceso."""
    if youth_id:
        if not _check_youth_access(db, user, youth_id):
            raise HTTPException(status_code=403, detail="Acceso denegado")
        return db.query(SessionModel).filter(SessionModel.youth_id == youth_id)

    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        if not youth:
            return None
        return db.query(SessionModel).filter(SessionModel.youth_id == youth.id)

    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof:
            return None
        youth_ids_subq = select(Assignment.youth_id).where(
            Assignment.professional_id == prof.id,
            Assignment.status == "ACTIVO",
        )
        return db.query(SessionModel).filter(SessionModel.youth_id.in_(youth_ids_subq))

    return None


@router.post("", response_model=SessionResponse)
def create_session(
    data: SessionCreate,
    request: Request,
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
    request_id = getattr(request.state, "request_id", "unknown")
    db.add(SessionEvent(
        session_id=session.id,
        event_type="CREATED",
        payload={"source": "backend", "request_id": request_id},
    ))
    db.commit()
    db.refresh(session)
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
    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50

    sessions_q = _build_sessions_query(db, user, youth_id)
    if sessions_q is None:
        if use_pagination and response:
            response.headers["X-Total-Count"] = "0"
            response.headers["X-Page"] = str(page)
            response.headers["X-Page-Size"] = str(page_size)
        return []

    if search and search.strip():
        term = f"%{search.strip()}%"
        cleaned = re.sub(r"[^0-9kK]", "", search).upper()
        conditions = [
            Youth.display_name.ilike(term),
            Youth.rut.ilike(term),
            Youth.identifier.ilike(term),
        ]
        if cleaned:
            rut_norm = func.replace(func.replace(func.upper(Youth.rut), ".", ""), "-", "")
            conditions.append(rut_norm.ilike(f"%{cleaned}%"))
        sessions_q = sessions_q.join(Youth, Youth.id == SessionModel.youth_id).filter(or_(*conditions))

    if status:
        allowed_status = {"EN_CURSO", "COMPLETADA", "CANCELADA", "ERROR"}
        if status not in allowed_status:
            raise HTTPException(status_code=400, detail="Estado de sesión inválido")
        sessions_q = sessions_q.filter(SessionModel.status == status)

    if mode:
        allowed_modes = {"AUTOGESTIONADA", "SUPERVISADA"}
        if mode not in allowed_modes:
            raise HTTPException(status_code=400, detail="Modo de sesión inválido")
        sessions_q = sessions_q.filter(SessionModel.mode == mode)

    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="Rango de fechas inválido")

    if start_date:
        start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        sessions_q = sessions_q.filter(SessionModel.started_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        sessions_q = sessions_q.filter(SessionModel.started_at <= end_dt)

    total = None
    if use_pagination:
        total = sessions_q.order_by(None).count()
        if response:
            response.headers["X-Total-Count"] = str(total)
            response.headers["X-Page"] = str(page)
            response.headers["X-Page-Size"] = str(page_size)
        sessions_q = sessions_q.order_by(SessionModel.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
    else:
        sessions_q = sessions_q.order_by(SessionModel.started_at.desc())

    sessions = sessions_q.all()
    return [SessionResponse.model_validate(s) for s in sessions]


class SessionMonthlyStat(BaseModel):
    month: str
    count: int


class SessionStatsResponse(BaseModel):
    total: int
    completed: int
    cancelled: int
    error: int
    in_progress: int
    monthly: list[SessionMonthlyStat]


@router.get("/stats", response_model=SessionStatsResponse)
def get_session_stats(
    youth_id: int | None = Query(None),
    months: int = Query(6, ge=1, le=24),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resumen de sesiones (conteos por estado y curva mensual de completadas)."""
    sessions_q = _build_sessions_query(db, user, youth_id)
    now = datetime.now(timezone.utc)

    def _month_key(year: int, month: int) -> str:
        return f"{year}-{month:02d}"

    month_keys: list[str] = []
    for i in range(months - 1, -1, -1):
        m = now.month - i
        y = now.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        month_keys.append(_month_key(y, m))
    first_year, first_month = month_keys[0].split("-")
    start_date = datetime(int(first_year), int(first_month), 1, tzinfo=timezone.utc)

    if sessions_q is None:
        return SessionStatsResponse(
            total=0,
            completed=0,
            cancelled=0,
            error=0,
            in_progress=0,
            monthly=[SessionMonthlyStat(month=k, count=0) for k in month_keys],
        )

    totals = sessions_q.with_entities(
        func.count(SessionModel.id).label("total"),
        func.sum(case((SessionModel.status == "COMPLETADA", 1), else_=0)).label("completed"),
        func.sum(case((SessionModel.status == "CANCELADA", 1), else_=0)).label("cancelled"),
        func.sum(case((SessionModel.status == "ERROR", 1), else_=0)).label("error"),
        func.sum(case((SessionModel.status == "EN_CURSO", 1), else_=0)).label("in_progress"),
    ).first()

    month_rows = (
        sessions_q
        .filter(
            SessionModel.status == "COMPLETADA",
            SessionModel.ended_at.isnot(None),
            SessionModel.ended_at >= start_date,
        )
        .with_entities(func.date_trunc("month", SessionModel.ended_at).label("month"), func.count(SessionModel.id))
        .group_by("month")
        .all()
    )
    month_counts = {}
    for month_dt, count in month_rows:
        if month_dt:
            month_counts[_month_key(month_dt.year, month_dt.month)] = int(count or 0)

    return SessionStatsResponse(
        total=int(totals.total or 0),
        completed=int(totals.completed or 0),
        cancelled=int(totals.cancelled or 0),
        error=int(totals.error or 0),
        in_progress=int(totals.in_progress or 0),
        monthly=[SessionMonthlyStat(month=k, count=month_counts.get(k, 0)) for k in month_keys],
    )


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
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Inicia la experiencia con LiveAvatar: PATCH contexto, token, start. Devuelve livekit_url+access_token o embed de respaldo."""
    from app.models.simulation_template import SimulationTemplate
    from app.models.job_role import JobRole
    from app.models.case import Case
    from app.services.liveavatar import (
        start_liveavatar_session,
        LiveAvatarError,
        is_liveavatar_configured,
        get_liveavatar_config_status,
    )

    request_id = getattr(request.state, "request_id", "unknown")

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

    fallback_reason = None
    fallback_detail = None
    fallback_status = None
    config_status = get_liveavatar_config_status(template)

    # Integración LiveAvatar si está configurada
    if is_liveavatar_configured(template):
        try:
            # Payload minimo para el generador de prompt dinamico
            prompt_input = PromptInput(
                alumno_id=str(session.youth_id),
                cargo_id=job_role.slug,
                case_id=case.slug,
                session_id=session.id,
                metadata={
                    "mode": session.mode,
                    "simulation_template_id": session.simulation_template_id,
                },
            )
            result = start_liveavatar_session(
                job_role,
                case,
                template,
                request_id=request_id,
                prompt_input=prompt_input,
            )
            live_id = result.get("session_id") or f"live-{session_id}"
            session.liveavatar_session_id = str(live_id)
            db.add(SessionEvent(
                session_id=session.id,
                event_type="LIVEAVATAR_STARTED",
                payload={"liveavatar_session_id": live_id, "request_id": request_id},
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
            fallback_reason = "LIVEAVATAR_ERROR"
            fallback_detail = e.message
            fallback_status = e.status_code
            logger.warning(
                "request_id=%s liveavatar_error status=%s detail=%s",
                request_id,
                e.status_code,
                e.message,
            )
    else:
        fallback_reason = "NOT_CONFIGURED"
        fallback_detail = "LiveAvatar no configurado"
        logger.warning(
            "request_id=%s liveavatar_fallback reason=NOT_CONFIGURED api_key=%s context_id=%s avatar_id=%s voice_id=%s",
            request_id,
            config_status.get("api_key"),
            config_status.get("context_id"),
            config_status.get("avatar_id"),
            config_status.get("voice_id"),
        )

    if fallback_reason:
        payload = {
            "reason": fallback_reason,
            "detail": fallback_detail,
            "request_id": request_id,
        }
        if fallback_status:
            payload["status_code"] = fallback_status
        if fallback_reason == "NOT_CONFIGURED":
            payload["config_status"] = config_status
        db.add(SessionEvent(
            session_id=session.id,
            event_type="LIVEAVATAR_FALLBACK",
            payload=payload,
        ))

    # Marcador de posicion si LiveAvatar no esta configurado
    live_id = f"live-{session_id}-{int(datetime.now(timezone.utc).timestamp())}"
    session.liveavatar_session_id = live_id
    db.add(SessionEvent(
        session_id=session.id,
        event_type="LIVEAVATAR_STARTED",
        payload={"liveavatar_session_id": live_id, "request_id": request_id},
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
    request: Request,
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
    request_id = getattr(request.state, "request_id", "unknown")

    if session.liveavatar_session_id:
        transcript_data = get_session_transcript(session.liveavatar_session_id, request_id=request_id)
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

            # Evaluar transcripción con IA externa (no bloquea el cierre si falla)
            transcript_text = _transcript_to_text(transcript_data.get("transcript_data", []))
            if transcript_text:
                try:
                    eval_input = EvaluationInput(
                        alumno_id=str(session.youth_id),
                        session_id=session.id,
                        transcript=transcript_text,
                    )
                    eval_result = evaluate(eval_input, request_id=request_id)
                    if eval_result.snapshot:
                        metrics = dict(session.metrics) if session.metrics else {}
                        metrics["prompt_evaluation"] = eval_result.snapshot
                        metrics["prompt_evaluation_provider"] = eval_result.provider
                        if eval_result.version:
                            metrics["prompt_evaluation_version"] = eval_result.version
                        session.metrics = metrics
                        db.add(SessionEvent(
                            session_id=session.id,
                            event_type="PROMPT_EVALUATED",
                            payload={"provider": eval_result.provider, "request_id": request_id},
                        ))
                except PromptProviderError as e:
                    logger.warning(
                        "request_id=%s prompt_evaluation_error detail=%s",
                        request_id,
                        str(e),
                    )
                except Exception as e:
                    logger.warning(
                        "request_id=%s prompt_evaluation_unexpected detail=%s",
                        request_id,
                        str(e),
                    )

    payload = {"status": data.status, "request_id": request_id}
    if data.motivo:
        payload["motivo"] = data.motivo
    db.add(SessionEvent(session_id=session.id, event_type="ENDED", payload=payload))

    if data.status == "COMPLETADA":
        upsert_youth_notification(
            db,
            youth_id=session.youth_id,
            type="session",
            title="Entrevista completada",
            message="Tu entrevista fue guardada en el historial.",
            link=f"/joven/simulacion/{session.id}",
            entity_type="session",
            entity_id=session.id,
        )
    db.commit()
    db.refresh(session)
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

    if not data.session_id and not data.liveavatar_session_id:
        raise HTTPException(status_code=400, detail="session_id o liveavatar_session_id requerido")

    session = None
    if data.session_id:
        session = db.query(SessionModel).filter(SessionModel.id == data.session_id).first()
    elif data.liveavatar_session_id:
        session = db.query(SessionModel).filter(
            SessionModel.liveavatar_session_id == data.liveavatar_session_id
        ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    metrics = dict(session.metrics) if session.metrics else {}
    metrics["liveavatar_evaluation"] = data.evaluation
    metrics["liveavatar_evaluation_source"] = data.source or "liveavatar"
    metrics["liveavatar_evaluation_received_at"] = datetime.now(timezone.utc).isoformat()
    session.metrics = metrics

    request_id = getattr(request.state, "request_id", "unknown")
    db.add(
        SessionEvent(
            session_id=session.id,
            event_type="LIVEAVATAR_EVALUATION",
            payload={"source": data.source or "liveavatar", "request_id": request_id},
        )
    )

    db.commit()
    return {"ok": True, "session_id": session.id}


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
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not _check_youth_access(db, user, session.youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo vacío")

    ext = Path(file.filename).suffix.lower()
    if ext not in SESSION_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Permitidas: {', '.join(sorted(SESSION_AUDIO_EXTENSIONS))}",
        )

    _ensure_session_audio_dir()
    filename = f"session_{session_id}_{uuid.uuid4().hex}{ext}"
    file_path = SESSION_AUDIO_DIR / filename
    try:
        size = _save_audio_stream(file, file_path)
    except HTTPException:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise
    except OSError as e:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error al guardar audio: {str(e)}")
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    base = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    url = f"{base}/uploads/audio/{filename}"

    existing = db.query(SessionAudio).filter(SessionAudio.session_id == session_id).first()
    if existing:
        # Limpia archivo anterior si pertenece a uploads/audio
        try:
            old_url = existing.url or ""
            if "/uploads/audio/" in old_url:
                old_name = old_url.split("/uploads/audio/")[-1]
                old_path = SESSION_AUDIO_DIR / old_name
                if old_path.exists():
                    old_path.unlink(missing_ok=True)
        except Exception:
            pass
        existing.url = url
        existing.content_type = file.content_type
        existing.file_size_bytes = size
        existing.duration_seconds = duration_seconds
        db.commit()
        db.refresh(existing)
        return SessionAudioResponse.model_validate(existing)

    audio = SessionAudio(
        session_id=session_id,
        url=url,
        content_type=file.content_type,
        file_size_bytes=size,
        duration_seconds=duration_seconds,
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)
    return SessionAudioResponse.model_validate(audio)


@router.get("/{session_id}/audio", response_model=SessionAudioResponse | None)
def get_session_audio(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene metadata del audio de una sesión. Requiere acceso a la sesión."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not _check_youth_access(db, user, session.youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    audio = db.query(SessionAudio).filter(SessionAudio.session_id == session_id).first()
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

