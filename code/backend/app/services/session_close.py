"""Cierre de sesión de simulación: métricas, transcripción LiveAvatar, evaluación de prompt."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session as OrmSession

from app.models.session import Session as SessionModel
from app.models.session_event import SessionEvent
from app.models.session_transcript import SessionTranscript
from app.schemas.prompt import EvaluationInput
from app.schemas.session import SessionCloseRequest
from app.services import liveavatar
from app.services.notifications import upsert_youth_notification
from app.services.prompt_engine import PromptProviderError, evaluate

logger = logging.getLogger("elvir.api")


def _transcript_to_text(transcript_data: list[dict] | None) -> str:
    """Convierte transcript_data (lista de turnos) a texto plano."""
    lines: list[str] = []
    for item in transcript_data or []:
        role = (item.get("role") or "speaker").strip()
        text = (item.get("transcript") or "").strip()
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines).strip()


def apply_close_session(
    db: OrmSession,
    session: SessionModel,
    data: SessionCloseRequest,
    request_id: str,
) -> None:
    """
    Actualiza la sesión al cierre, persiste transcripción/evaluación si aplica, notifica y hace commit.
    El caller debe haber resuelto la sesión y permisos.
    """
    session.status = data.status
    session.ended_at = datetime.now(UTC)
    metrics = dict(data.metrics) if data.metrics else {}
    if data.motivo:
        metrics["motivo"] = data.motivo
    if "duration_seconds" in metrics:
        session.duration_seconds = metrics["duration_seconds"]
    else:
        if session.started_at:
            delta = datetime.now(UTC) - session.started_at
            session.duration_seconds = int(delta.total_seconds())
    session.metrics = metrics if metrics else data.metrics

    if data.status == "COMPLETADA" and session.liveavatar_session_id:
        transcript_data = liveavatar.get_session_transcript(session.liveavatar_session_id, request_id=request_id)
        if transcript_data:
            existing = db.query(SessionTranscript).filter(SessionTranscript.session_id == session.id).first()
            if existing:
                existing.transcript_data = transcript_data.get("transcript_data", [])
                existing.session_active = transcript_data.get("session_active")
                existing.fetched_at = datetime.now(UTC)
            else:
                db.add(
                    SessionTranscript(
                        session_id=session.id,
                        transcript_data=transcript_data.get("transcript_data", []),
                        session_active=transcript_data.get("session_active"),
                    )
                )

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
                        db.add(
                            SessionEvent(
                                session_id=session.id,
                                event_type="PROMPT_EVALUATED",
                                payload={"provider": eval_result.provider, "request_id": request_id},
                            )
                        )
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
