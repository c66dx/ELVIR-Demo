"""Router de jóvenes."""
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc, or_

from app.database import get_db
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation
from app.models.assignment import Assignment
from app.models.session import Session as SessionModel
from app.models.platform_session import PlatformSession
from app.schemas.youth import YouthCreate, YouthUpdate, YouthResponse, YouthWithLastSession, LastSessionInfo, YouthChangeEmailRequest, parse_profile_checklist
from app.schemas.platform_session import PlatformSessionResponse
from app.core.dependencies import get_current_user, get_current_professional

router = APIRouter(prefix="/youths", tags=["youths"])


def _generate_identifier(db: DBSession) -> str:
    """Genera el siguiente identificador (JOV-001, JOV-002, ...)."""
    youths = db.query(Youth.identifier).filter(Youth.identifier.isnot(None)).all()
    max_num = 0
    for (ident,) in youths:
        if ident and ident.startswith("JOV-"):
            try:
                n = int(ident[4:].strip())
                max_num = max(max_num, n)
            except ValueError:
                pass
    return f"JOV-{max_num + 1:03d}"


def _youth_to_response(youth: Youth, activation_url: str | None = None, email: str | None = None) -> YouthResponse:
    """Convierte modelo Youth a YouthResponse. email viene del User cuando youth.user_id existe."""
    return YouthResponse(
        id=youth.id,
        user_id=youth.user_id,
        display_name=youth.display_name,
        identifier=youth.identifier,
        email=email,
        phone=youth.phone,
        year_of_birth=youth.year_of_birth,
        diagnosis=youth.diagnosis,
        login_enabled=youth.login_enabled,
        is_active=youth.is_active,
        general_notes=youth.general_notes,
        profile_checklist=parse_profile_checklist(youth.profile_checklist) or None,
        activation_url=activation_url,
    )


@router.get("", response_model=list[YouthWithLastSession])
def list_youths(
    search: str | None = None,
    is_active: bool | None = None,
    login_enabled: bool | None = None,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Lista jóvenes. PROFESIONAL: asignados. JOVEN: solo su propio perfil.
    Filtros: search (nombre/identificador), is_active, login_enabled."""
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
        q = db.query(Youth).filter(Youth.id.in_(youth_ids))
        if is_active is not None:
            q = q.filter(Youth.is_active == is_active)
        if login_enabled is not None:
            q = q.filter(Youth.login_enabled == login_enabled)
        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.filter(or_(Youth.display_name.ilike(term), Youth.identifier.ilike(term)))
        youths = q.all()
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
        email = _get_youth_email(db, y.user_id) if y.user_id else None
        result.append(
            YouthWithLastSession(
                id=y.id,
                user_id=y.user_id,
                display_name=y.display_name,
                identifier=y.identifier,
                email=email,
                phone=y.phone,
                year_of_birth=y.year_of_birth,
                diagnosis=y.diagnosis,
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
    """Crea joven y asignación automática. identifier lo genera el sistema. Si login_enabled+email: genera invitación."""
    profile_checklist_json = json.dumps(data.profile_checklist) if data.profile_checklist else None
    identifier = _generate_identifier(db)
    youth = Youth(
        display_name=data.display_name,
        identifier=identifier,
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


def _get_youth_email(db: DBSession, user_id: int) -> str | None:
    """Obtiene el email del User cuando user_id existe."""
    user = db.query(User).filter(User.id == user_id).first()
    return user.email if user else None


def _get_pending_invitation_email(db: DBSession, youth_id: int) -> str | None:
    """Obtiene el email de la invitación pendiente (sin usar) más reciente."""
    inv = (
        db.query(YouthInvitation)
        .filter(YouthInvitation.youth_id == youth_id, YouthInvitation.used_at.is_(None))
        .order_by(desc(YouthInvitation.created_at))
        .first()
    )
    return inv.email if inv else None


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
    email = _get_youth_email(db, youth.user_id) if youth.user_id else _get_pending_invitation_email(db, youth.id)
    return _youth_to_response(youth, email=email)


@router.get("/{youth_id}/platform-sessions", response_model=list[PlatformSessionResponse])
def list_youth_platform_sessions(
    youth_id: int,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Lista entradas/salidas del joven a la plataforma (login/logout). Solo si tiene user_id."""
    youth = db.query(Youth).filter(Youth.id == youth_id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")
    if not youth.user_id:
        return []
    if user.role == "JOVEN" and youth.user_id != user.id:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if user.role == "ADMIN":
        pass
    elif user.role == "PROFESIONAL":
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
    sessions = (
        db.query(PlatformSession)
        .filter(PlatformSession.user_id == youth.user_id)
        .order_by(desc(PlatformSession.started_at))
        .limit(50)
        .all()
    )
    return [PlatformSessionResponse.model_validate(s) for s in sessions]


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
    update_data.pop("identifier", None)  # no editable
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
    email = _get_youth_email(db, youth.user_id) if youth.user_id else None
    return _youth_to_response(youth, activation_url=activation_url, email=email)


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
    email = _get_youth_email(db, youth.user_id) if youth.user_id else None
    return _youth_to_response(youth, email=email)


@router.post("/{youth_id}/change-email", response_model=YouthResponse)
def change_youth_email(
    youth_id: int,
    data: YouthChangeEmailRequest,
    prof=Depends(get_current_professional),
    db: DBSession = Depends(get_db),
):
    """Cambia el email del joven y genera nuevo enlace de activación. Requiere login habilitado."""
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
    if not youth.login_enabled:
        raise HTTPException(status_code=400, detail="El joven no tiene login habilitado")
    new_email = data.new_email.lower().strip()
    if not new_email:
        raise HTTPException(status_code=400, detail="Email inválido")
    existing = db.query(User).filter(User.email.ilike(new_email)).first()
    if existing and (not youth.user_id or existing.id != youth.user_id):
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    db.add(YouthInvitation(youth_id=youth.id, email=new_email, token=token, expires_at=expires))
    from app.config import settings
    activation_url = f"{settings.APP_BASE_URL}/activar?token={token}"
    if youth.user_id:
        user = db.query(User).filter(User.id == youth.user_id).first()
        if user:
            user.email = new_email
    db.commit()
    db.refresh(youth)
    email = _get_youth_email(db, youth.user_id) if youth.user_id else None
    return _youth_to_response(youth, activation_url=activation_url, email=email)


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
    email = _get_youth_email(db, youth.user_id) if youth.user_id else None
    return _youth_to_response(youth, email=email)
