"""Router de profesionales (gestión por Admin)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator

from app.database import get_db
from app.models.user import User
from app.models.professional import Professional
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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista asignaciones de un profesional. Solo el propio profesional o Admin."""
    if not _can_access_professional(user, professional_id, db):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    items = db.query(Assignment).filter(
        Assignment.professional_id == professional_id,
    ).order_by(Assignment.assigned_at.desc()).all()
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
    is_active: bool


class ProfessionalUpdate(BaseModel):
    display_name: str
    specialty: str | None = None
    institution: str | None = None
    is_active: bool | None = None


@router.get("", response_model=list[ProfessionalResponse])
def list_professionals(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Lista todos los profesionales. Solo Admin."""
    profs = db.query(Professional).filter(Professional.is_active == True).order_by(Professional.id).all()
    return [
        ProfessionalResponse(
            id=p.id,
            user_id=p.user_id,
            display_name=p.display_name,
            specialty=p.specialty,
            institution=p.institution,
            is_active=p.is_active,
        )
        for p in profs
    ]


class ProfessionalCreate(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato de email inválido")
        return v.lower()
    display_name: str
    specialty: str | None = None
    institution: str | None = None


@router.post("", response_model=ProfessionalResponse)
def create_professional(
    data: ProfessionalCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Crea un nuevo profesional. Solo Admin."""
    existing = db.query(User).filter(User.email.ilike(data.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    user = User(
        email=data.email.lower(),
        password_hash=get_password_hash(data.password),
        role="PROFESIONAL",
        is_active=True,
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
    db.commit()
    db.refresh(prof)
    return ProfessionalResponse(
        id=prof.id,
        user_id=prof.user_id,
        display_name=prof.display_name,
        specialty=prof.specialty,
        institution=prof.institution,
        is_active=prof.is_active,
    )


@router.get("/{professional_id}", response_model=ProfessionalResponse)
def get_professional(
    professional_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Obtiene el detalle de un profesional. Solo Admin."""
    prof = db.query(Professional).filter(Professional.id == professional_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    return ProfessionalResponse(
        id=prof.id,
        user_id=prof.user_id,
        display_name=prof.display_name,
        specialty=prof.specialty,
        institution=prof.institution,
        is_active=prof.is_active,
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
    db.commit()
    db.refresh(prof)
    return ProfessionalResponse(
        id=prof.id,
        user_id=prof.user_id,
        display_name=prof.display_name,
        specialty=prof.specialty,
        institution=prof.institution,
        is_active=prof.is_active,
    )
