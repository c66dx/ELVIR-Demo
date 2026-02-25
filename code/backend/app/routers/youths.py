"""Router de jóvenes."""
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc

from app.database import get_db
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation
from app.models.assignment import Assignment
from app.models.session import Session as SessionModel
from app.schemas.youth import YouthCreate, YouthUpdate, YouthResponse, YouthWithLastSession, LastSessionInfo, parse_profile_checklist
from app.core.dependencies import get_current_user, get_current_professional

router = APIRouter(prefix="/youths", tags=["youths"])


def _youth_to_response(youth: Youth, activation_url: str | None = None) -> YouthResponse:
    """Convierte modelo Youth a YouthResponse, opcionalmente con activation_url."""
    return YouthResponse(
        id=youth.id,
        display_name=youth.display_name,
        identifier=youth.identifier,
        phone=youth.phone,
        login_enabled=youth.login_enabled,
        is_active=youth.is_active,
        general_notes=youth.general_notes,
        profile_checklist=parse_profile_checklist(youth.profile_checklist) or None,
        activation_url=activation_url,
    )


@router.get("", response_model=list[YouthWithLastSession])
def list_youths(
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Lista jóvenes. PROFESIONAL: asignados. JOVEN: solo su propio perfil."""
    if user.role == "PROFESIONAL":
        from app.models.professional import Professional
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof:
            return []
        assignment_ids = db.query(Assignment.youth_id).filter(
            Assignment.professional_id == prof.id,
            Assignment.status == "ACTIVO",
        ).all()
        youth_ids = {a[0] for a in assignment_ids}
        youths = db.query(Youth).filter(Youth.id.in_(youth_ids)).all()
    else:
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        youths = [youth] if youth else []
    result = []
    for y in youths:
        last_sess = (
            db.query(SessionModel)
            .filter(SessionModel.youth_id == y.id)
            .order_by(desc(SessionModel.started_at))
            .first()
        )
        status_label = "Con sesiones" if last_sess else "Sin sesiones"
        last_session = None
        if last_sess:
            last_session = LastSessionInfo(
                id=last_sess.id,
                started_at=last_sess.started_at,
                status=last_sess.status,
                ended_at=last_sess.ended_at,
            )
        result.append(
            YouthWithLastSession(
                id=y.id,
                display_name=y.display_name,
                identifier=y.identifier,
                phone=y.phone,
                login_enabled=y.login_enabled,
                is_active=y.is_active,
                general_notes=y.general_notes,
                profile_checklist=parse_profile_checklist(y.profile_checklist) or None,
                status_label=status_label,
                last_session=last_session,
            )
        )
    return result


@router.post("", response_model=YouthResponse)
def create_youth(
    data: YouthCreate,
    prof=Depends(get_current_professional),
    db: DBSession = Depends(get_db),
):
    """Crea joven y asignación automática. Si login_enabled+email: genera invitación y activation_url."""
    profile_checklist_json = json.dumps(data.profile_checklist) if data.profile_checklist else None
    youth = Youth(
        display_name=data.display_name,
        identifier=data.identifier,
        phone=data.phone,
        login_enabled=data.login_enabled,
        general_notes=data.general_notes,
        profile_checklist=profile_checklist_json,
        is_active=True,
    )
    db.add(youth)
    db.flush()
    db.add(Assignment(youth_id=youth.id, professional_id=prof.id, status="ACTIVO"))
    db.flush()
    activation_url = None
    if data.login_enabled and data.email:
        token = str(uuid.uuid4())
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        db.add(YouthInvitation(youth_id=youth.id, email=data.email.lower(), token=token, expires_at=expires))
        from app.config import settings
        activation_url = f"{settings.APP_BASE_URL}/activar?token={token}"
    db.commit()
    return _youth_to_response(youth, activation_url)


@router.get("/{youth_id}", response_model=YouthResponse)
def get_youth(
    youth_id: int,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Obtiene perfil de joven. Requiere ser el propio joven o profesional asignado."""
    youth = db.query(Youth).filter(Youth.id == youth_id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")
    if user.role == "JOVEN" and youth.user_id != user.id:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if user.role == "PROFESIONAL":
        from app.models.professional import Professional
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if prof:
            assign = db.query(Assignment).filter(
                Assignment.youth_id == youth_id,
                Assignment.professional_id == prof.id,
                Assignment.status == "ACTIVO",
            ).first()
            if not assign:
                raise HTTPException(status_code=403, detail="Acceso denegado")
    return _youth_to_response(youth)


@router.put("/{youth_id}", response_model=YouthResponse)
def update_youth(
    youth_id: int,
    data: YouthUpdate,
    prof=Depends(get_current_professional),
    db: DBSession = Depends(get_db),
):
    """Actualiza perfil de joven. Si habilita login sin user_id: genera nueva invitación."""
    youth = db.query(Youth).filter(Youth.id == youth_id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")
    assign = db.query(Assignment).filter(
        Assignment.youth_id == youth_id,
        Assignment.professional_id == prof.id,
        Assignment.status == "ACTIVO",
    ).first()
    if not assign:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    update_data = data.model_dump(exclude_unset=True)
    email = update_data.pop("email", None)
    profile_checklist = update_data.pop("profile_checklist", None)
    for k, v in update_data.items():
        setattr(youth, k, v)
    if profile_checklist is not None:
        youth.profile_checklist = json.dumps(profile_checklist) if profile_checklist else None
    activation_url = None
    if youth.login_enabled and not youth.user_id and email:
        token = str(uuid.uuid4())
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        db.add(YouthInvitation(youth_id=youth.id, email=email.lower(), token=token, expires_at=expires))
        from app.config import settings
        activation_url = f"{settings.APP_BASE_URL}/activar?token={token}"
    db.commit()
    db.refresh(youth)
    return _youth_to_response(youth, activation_url)


@router.patch("/{youth_id}/deactivate", response_model=YouthResponse)
def deactivate_youth(
    youth_id: int,
    prof=Depends(get_current_professional),
    db: DBSession = Depends(get_db),
):
    """Desactiva joven (soft delete). Solo profesional asignado."""
    youth = db.query(Youth).filter(Youth.id == youth_id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")
    assign = db.query(Assignment).filter(
        Assignment.youth_id == youth_id,
        Assignment.professional_id == prof.id,
        Assignment.status == "ACTIVO",
    ).first()
    if not assign:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    youth.is_active = False
    db.commit()
    db.refresh(youth)
    return _youth_to_response(youth)


@router.patch("/{youth_id}/activate", response_model=YouthResponse)
def activate_youth(
    youth_id: int,
    prof=Depends(get_current_professional),
    db: DBSession = Depends(get_db),
):
    """Reactiva joven. Solo profesional asignado."""
    youth = db.query(Youth).filter(Youth.id == youth_id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")
    assign = db.query(Assignment).filter(
        Assignment.youth_id == youth_id,
        Assignment.professional_id == prof.id,
        Assignment.status == "ACTIVO",
    ).first()
    if not assign:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    youth.is_active = True
    db.commit()
    db.refresh(youth)
    return _youth_to_response(youth)
