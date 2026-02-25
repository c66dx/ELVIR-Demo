"""Router de profesionales (gestión por Admin)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator

from app.database import get_db
from app.models.user import User
from app.models.professional import Professional
from app.core.security import get_password_hash
from app.core.dependencies import get_current_admin

router = APIRouter(prefix="/professionals", tags=["professionals"])


class ProfessionalResponse(BaseModel):
    id: int
    user_id: int
    display_name: str
    specialty: str | None
    institution: str | None
    is_active: bool


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
