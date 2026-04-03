"""Inicio de sesión LiveAvatar: contexto, token, embed de respaldo."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy.orm import Session as OrmSession

from app.models.case import Case
from app.models.job_role import JobRole
from app.models.session import Session as SessionModel
from app.models.session_event import SessionEvent
from app.models.simulation_template import SimulationTemplate
from app.schemas.prompt import PromptInput
from app.schemas.session import SessionStartResponse
from app.services import liveavatar

logger = logging.getLogger("elvir.api")


def apply_start_session(
    db: OrmSession,
    session: SessionModel,
    session_id: int,
    request_id: str,
) -> SessionStartResponse:
    """
    Arranca LiveAvatar o devuelve embed de respaldo. Actualiza heartbeat implícito vía caller si aplica.
    El caller debe haber validado sesión EN_CURSO y permisos.
    """
    template = db.query(SimulationTemplate).filter(SimulationTemplate.id == session.simulation_template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    job_role = db.query(JobRole).filter(JobRole.id == template.job_role_id).first()
    case = db.query(Case).filter(Case.id == template.case_id).first()
    if not job_role or not case:
        raise HTTPException(status_code=404, detail="Cargo o caso no encontrado")

    fallback_reason = None
    fallback_detail = None
    fallback_status = None
    config_status = liveavatar.get_liveavatar_config_status(template)

    if liveavatar.is_liveavatar_configured(template):
        try:
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
            result = liveavatar.start_liveavatar_session(
                job_role,
                case,
                template,
                request_id=request_id,
                prompt_input=prompt_input,
            )
            live_id = result.get("session_id") or f"live-{session_id}"
            session.liveavatar_session_id = str(live_id)
            db.add(
                SessionEvent(
                    session_id=session.id,
                    event_type="LIVEAVATAR_STARTED",
                    payload={"liveavatar_session_id": live_id, "request_id": request_id},
                )
            )
            db.commit()
            db.refresh(session)
            return SessionStartResponse(
                session_id=session.id,
                liveavatar_session_id=str(live_id),
                livekit_url=result.get("livekit_url"),
                access_token=result.get("access_token"),
            )
        except liveavatar.LiveAvatarError as e:
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
        fallback_detail = liveavatar.describe_liveavatar_config_gaps(template)
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
        db.add(
            SessionEvent(
                session_id=session.id,
                event_type="LIVEAVATAR_FALLBACK",
                payload=payload,
            )
        )

    live_id = f"live-{session_id}-{int(datetime.now(UTC).timestamp())}"
    session.liveavatar_session_id = live_id
    db.add(
        SessionEvent(
            session_id=session.id,
            event_type="LIVEAVATAR_STARTED",
            payload={"liveavatar_session_id": live_id, "request_id": request_id},
        )
    )
    db.commit()
    db.refresh(session)
    placeholder_url = "data:text/html;charset=utf-8," + quote(
        "<html><body style='display:flex;align-items:center;justify-content:center;height:100%;font-family:sans-serif'><p>Simulación LiveAvatar (configurar LIVEAVATAR_* en .env)</p></body></html>"
    )
    hint = (fallback_detail or "Sin conexión a LiveAvatar real.").strip()
    if len(hint) > 800:
        hint = hint[:797] + "..."
    logger.warning("session_id=%s liveavatar_fallback_embed detail=%s", session_id, hint)
    return SessionStartResponse(
        session_id=session.id,
        liveavatar_session_id=live_id,
        embed={"type": "iframe", "url": placeholder_url},
        fallback_detail=hint,
    )
