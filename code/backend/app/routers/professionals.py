"""Router de profesionales (gestión por Admin)."""
from datetime import datetime, timedelta, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.professional import Professional
from app.models.professional_invitation import ProfessionalInvitation
from app.models.assignment import Assignment
from app.core.security import get_password_hash
from app.core.dependencies import get_current_admin, get_current_user

router = APIRouter(prefix="/professionals", tags=["professionals"])


def _can_access_professional(user: User, professional_id: int, db: Session) -> bool:
    """Verifica si el usuario puede acceder a las asignaciones del profesional."""
    if user.role == "ADMIN":
        return True
    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        return prof is not None and prof.id == professional_id
    return False


@router.get("/{professional_id}/assignments")
def list_professional_assignments(
    professional_id: int,
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    response: Response = None,
):
    """Lista asignaciones de un profesional. Solo el propio profesional o Admin."""
    if not _can_access_professional(user, professional_id, db):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50

    q = db.query(Assignment).filter(Assignment.professional_id == professional_id)
    if use_pagination:
        total = q.order_by(None).count()
        if response:
            response.headers["X-Total-Count"] = str(total)
            response.headers["X-Page"] = str(page)
            response.headers["X-Page-Size"] = str(page_size)
        q = q.order_by(Assignment.assigned_at.desc()).offset((page - 1) * page_size).limit(page_size)
    else:
        q = q.order_by(Assignment.assigned_at.desc())

    items = q.all()
    return [
        {
            "id": a.id,
            "youth_id": a.youth_id,
            "professional_id": a.professional_id,
            "status": a.status,
            "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
            "ended_at": a.ended_at.isoformat() if a.ended_at else None,
        }
        for a in items
    ]


class ProfessionalResponse(BaseModel):
    id: int
    user_id: int
    display_name: str
    specialty: str | None
    institution: str | None
    profile_photo_url: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProfessionalCreateResponse(ProfessionalResponse):
    activation_url: str | None = None


class ProfessionalUpdate(BaseModel):
    display_name: str
    specialty: str | None = None
    institution: str | None = None
    is_active: bool | None = None


@router.get("", response_model=list[ProfessionalResponse])
def list_professionals(
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    is_active: bool | None = Query(None),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    response: Response = None,
):
    """Lista todos los profesionales. Solo Admin."""
    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50

    q = db.query(Professional)
    if is_active is not None:
        q = q.filter(Professional.is_active == is_active)

    if use_pagination:
        total = q.order_by(None).count()
        if response:
            response.headers["X-Total-Count"] = str(total)
            response.headers["X-Page"] = str(page)
            response.headers["X-Page-Size"] = str(page_size)
        q = q.order_by(Professional.id).offset((page - 1) * page_size).limit(page_size)
    else:
        q = q.order_by(Professional.id)
    profs = q.all()

    user_ids = [p.user_id for p in profs]
    user_rows = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
    user_map = {u.id: u for u in user_rows}

    return [
        ProfessionalResponse(
            id=p.id,
            user_id=p.user_id,
            display_name=p.display_name,
            specialty=p.specialty,
            institution=p.institution,
            profile_photo_url=user_map.get(p.user_id).profile_photo_url if user_map.get(p.user_id) else None,
            is_active=p.is_active,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in profs
    ]


class ProfessionalCreate(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato de email inválido")
        return v.lower()

    display_name: str
    specialty: str | None = None
    institution: str | None = None


@router.post("", response_model=ProfessionalCreateResponse)
def create_professional(
    data: ProfessionalCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Crea un nuevo profesional. Solo Admin."""
    existing = db.query(User).filter(User.email.ilike(data.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya est? registrado")

    temp_password = uuid.uuid4().hex
    user = User(
        email=data.email.lower(),
        password_hash=get_password_hash(temp_password),
        role="PROFESIONAL",
        is_active=False,
    )
    db.add(user)
    db.flush()

    prof = Professional(
        user_id=user.id,
        display_name=data.display_name,
        specialty=data.specialty,
        institution=data.institution,
        is_active=True,
    )
    db.add(prof)
    db.flush()

    now = datetime.now(timezone.utc)
    token = str(uuid.uuid4())
    expires = now + timedelta(days=7)
    db.add(
        ProfessionalInvitation(
            professional_id=prof.id,
            email=user.email,
            token=token,
            expires_at=expires,
        )
    )
    db.commit()
    db.refresh(prof)

    activation_url = f"{settings.APP_BASE_URL}/activar?token={token}"
    return ProfessionalCreateResponse(
        id=prof.id,
        user_id=prof.user_id,
        display_name=prof.display_name,
        specialty=prof.specialty,
        institution=prof.institution,
        profile_photo_url=user.profile_photo_url,
        is_active=prof.is_active,
        created_at=prof.created_at,
        updated_at=prof.updated_at,
        activation_url=activation_url,
    )


@router.get("/{professional_id}", response_model=ProfessionalResponse)
def get_professional(
    professional_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene el detalle de un profesional. Admin o el propio profesional."""
    if not _can_access_professional(user, professional_id, db):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    prof = db.query(Professional).filter(Professional.id == professional_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    linked_user = db.query(User).filter(User.id == prof.user_id).first() if prof.user_id else None
    return ProfessionalResponse(
        id=prof.id,
        user_id=prof.user_id,
        display_name=prof.display_name,
        specialty=prof.specialty,
        institution=prof.institution,
        profile_photo_url=linked_user.profile_photo_url if linked_user else None,
        is_active=prof.is_active,
        created_at=prof.created_at,
        updated_at=prof.updated_at,
    )


@router.put("/{professional_id}", response_model=ProfessionalResponse)
def update_professional(
    professional_id: int,
    data: ProfessionalUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Actualiza datos de perfil de un profesional (no credenciales). Solo Admin."""
    prof = db.query(Professional).filter(Professional.id == professional_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    prof.display_name = data.display_name
    prof.specialty = data.specialty
    prof.institution = data.institution
    if data.is_active is not None:
        prof.is_active = data.is_active
        if prof.user_id:
            user = db.query(User).filter(User.id == prof.user_id).first()
            if user:
                user.is_active = data.is_active
    db.commit()
    db.refresh(prof)
    linked_user = db.query(User).filter(User.id == prof.user_id).first() if prof.user_id else None
    return ProfessionalResponse(
        id=prof.id,
        user_id=prof.user_id,
        display_name=prof.display_name,
        specialty=prof.specialty,
        institution=prof.institution,
        profile_photo_url=linked_user.profile_photo_url if linked_user else None,
        is_active=prof.is_active,
        created_at=prof.created_at,
        updated_at=prof.updated_at,
    )
