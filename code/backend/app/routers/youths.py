"""Router de jóvenes."""
import json
import uuid
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request, status, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc, or_, func, and_
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation
from app.models.assignment import Assignment
from app.models.session import Session as SessionModel
from app.models.platform_session import PlatformSession
from app.models.notification import YouthNotification
from app.schemas.youth import YouthCreate, YouthUpdate, YouthResponse, YouthWithLastSession, LastSessionInfo, YouthChangeEmailRequest, parse_profile_checklist
from app.schemas.platform_session import PlatformSessionResponse
from app.schemas.notification import YouthNotificationResponse, NotificationReadRequest
from app.core.dependencies import get_current_user, get_current_professional

router = APIRouter(prefix="/youths", tags=["youths"])



MAX_IDENTIFIER_RETRIES = 3
YOUTH_PHOTO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
YOUTH_PHOTO_MAX_MB = 5
YOUTH_PHOTO_MAX_BYTES = YOUTH_PHOTO_MAX_MB * 1024 * 1024
YOUTH_PHOTO_CHUNK_SIZE = 1024 * 1024
YOUTH_PHOTO_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "youths"


def _ensure_youth_photo_dir() -> None:
    YOUTH_PHOTO_DIR.mkdir(parents=True, exist_ok=True)


def _save_youth_photo_stream(file: UploadFile, destination: Path) -> None:
    total_written = 0
    with destination.open("wb") as out:
        while True:
            chunk = file.file.read(YOUTH_PHOTO_CHUNK_SIZE)
            if not chunk:
                break
            total_written += len(chunk)
            if total_written > YOUTH_PHOTO_MAX_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Imagen demasiado grande. Máximo: {YOUTH_PHOTO_MAX_MB} MB",
                )
            out.write(chunk)


def _format_rut_body(body: str) -> str:
    parts = []
    while body:
        parts.append(body[-3:])
        body = body[:-3]
    return ".".join(reversed(parts))


def _compute_rut_dv(body: str) -> str:
    total = 0
    multiplier = 2
    for digit in reversed(body):
        total += int(digit) * multiplier
        multiplier = 2 if multiplier == 7 else multiplier + 1
    mod = 11 - (total % 11)
    if mod == 11:
        return "0"
    if mod == 10:
        return "K"
    return str(mod)


def _normalize_rut(value: str) -> str:
    cleaned = re.sub(r"[^0-9kK]", "", value or "").upper()
    if len(cleaned) < 2:
        raise HTTPException(status_code=400, detail="RUT inválido")
    body = cleaned[:-1]
    dv = cleaned[-1]
    if not body.isdigit():
        raise HTTPException(status_code=400, detail="RUT inválido")
    expected = _compute_rut_dv(body)
    if expected != dv:
        raise HTTPException(status_code=400, detail="RUT inválido")
    return f"{_format_rut_body(body)}-{dv}"


def _create_youth_with_unique_identifier(
    db: DBSession,
    *,
    display_name: str,
    rut: str | None = None,
    phone: str | None,
    year_of_birth: int | None = None,
    diagnosis: str | None = None,
    login_enabled: bool,
    general_notes: str | None,
    profile_checklist_json: str | None,
) -> Youth:
    """Crea Youth con reintento acotado ante colisión de identificador concurrente."""
    for _ in range(MAX_IDENTIFIER_RETRIES):
        identifier = _generate_identifier(db)
        try:
            with db.begin_nested():
                youth = Youth(
                    display_name=display_name,
                    identifier=identifier,
                    rut=rut,
                    phone=phone,
                    year_of_birth=year_of_birth,
                    diagnosis=diagnosis,
                    login_enabled=login_enabled,
                    general_notes=general_notes,
                    profile_checklist=profile_checklist_json,
                    photo_url=None,
                    is_active=True,
                )
                db.add(youth)
                db.flush()
                return youth
        except IntegrityError:
            continue

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="No fue posible generar un identificador único para el joven. Reintenta.",
    )


def _generate_identifier(db: DBSession) -> str:
    """Genera el siguiente identificador (JOV-001, JOV-002, ...)."""
    candidates = db.query(Youth.identifier).filter(Youth.identifier.like("JOV-%")).all()
    max_num = 0
    for (raw_ident,) in candidates:
        if not raw_ident:
            continue
        ident = raw_ident.strip()
        try:
            n = int(ident[4:])
            if n > max_num:
                max_num = n
        except (ValueError, IndexError):
            continue
    return f"JOV-{max_num + 1:03d}"


def _youth_to_response(
    youth: Youth,
    activation_url: str | None = None,
    email: str | None = None,
    profile_photo_url: str | None = None,
) -> YouthResponse:
    """Convierte modelo Youth a YouthResponse. email viene del User cuando youth.user_id existe."""
    final_photo_url = youth.photo_url or profile_photo_url
    return YouthResponse(
        id=youth.id,
        user_id=youth.user_id,
        display_name=youth.display_name,
        identifier=youth.identifier,
        rut=youth.rut,
        email=email,
        profile_photo_url=final_photo_url,
        phone=youth.phone,
        year_of_birth=youth.year_of_birth,
        diagnosis=youth.diagnosis,
        login_enabled=youth.login_enabled,
        is_active=youth.is_active,
        general_notes=youth.general_notes,
        profile_checklist=parse_profile_checklist(youth.profile_checklist) or None,
        activation_url=activation_url,
    )


def _get_last_session_map(db: DBSession, youth_ids: list[int]) -> dict[int, SessionModel]:
    """Obtiene última sesión por joven evitando query por cada registro (N+1)."""
    if not youth_ids:
        return {}

    latest_per_youth = (
        db.query(
            SessionModel.youth_id.label("youth_id"),
            func.max(SessionModel.started_at).label("max_started_at"),
        )
        .filter(SessionModel.youth_id.in_(youth_ids))
        .group_by(SessionModel.youth_id)
        .subquery()
    )

    sessions = (
        db.query(SessionModel)
        .join(
            latest_per_youth,
            and_(
                SessionModel.youth_id == latest_per_youth.c.youth_id,
                SessionModel.started_at == latest_per_youth.c.max_started_at,
            ),
        )
        .order_by(SessionModel.youth_id.asc(), SessionModel.started_at.desc(), SessionModel.id.desc())
        .all()
    )

    by_youth: dict[int, SessionModel] = {}
    for s in sessions:
        if s.youth_id not in by_youth:
            by_youth[s.youth_id] = s
    return by_youth


def _check_youth_access(db: DBSession, user: User, youth_id: int) -> bool:
    """Verifica si el usuario puede acceder al joven (propio, asignado o admin)."""
    if user.role == "ADMIN":
        return True
    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        return youth and youth.id == youth_id
    if user.role == "PROFESIONAL":
        from app.models.professional import Professional
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof:
            return False
        assign = db.query(Assignment).filter(
            Assignment.youth_id == youth_id,
            Assignment.professional_id == prof.id,
            Assignment.status == "ACTIVO",
        ).first()
        return assign is not None
    return False


def _get_user_email_map(db: DBSession, user_ids: list[int]) -> dict[int, str]:
    """Obtiene emails por user_id en una sola consulta."""
    if not user_ids:
        return {}
    users = db.query(User.id, User.email, User.is_active).filter(User.id.in_(user_ids)).all()
    return {u[0]: u[1] for u in users if u[2]}


def _get_user_profile_photo_map(db: DBSession, user_ids: list[int]) -> dict[int, str]:
    """Obtiene profile_photo_url por user_id en una sola consulta."""
    if not user_ids:
        return {}
    users = db.query(User.id, User.profile_photo_url).filter(User.id.in_(user_ids)).all()
    return {u[0]: u[1] for u in users if u[1]}


def _disable_youth_login(db: DBSession, youth: Youth) -> None:
    """Deshabilita login: desactiva usuario y libera email para reutilizar."""
    if youth.user_id:
        user = db.query(User).filter(User.id == youth.user_id).first()
        if user:
            user.is_active = False
            user.email = f"disabled+{user.id}@invalid.local"
    now = datetime.now(timezone.utc)
    (
        db.query(YouthInvitation)
        .filter(YouthInvitation.youth_id == youth.id, YouthInvitation.used_at.is_(None))
        .update({"used_at": now}, synchronize_session=False)
    )


@router.get("", response_model=list[YouthWithLastSession])
def list_youths(
    search: str | None = None,
    is_active: bool | None = None,
    login_enabled: bool | None = None,
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
    response: Response = None,
):
    """Lista jóvenes. PROFESIONAL: asignados. JOVEN: solo su propio perfil.
    Filtros: search (nombre/identificador), is_active, login_enabled."""
    if not isinstance(page, int):
        page = None
    if not isinstance(page_size, int):
        page_size = None

    if user.role == "PROFESIONAL":
        from app.models.professional import Professional
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof:
            return []
        q = (
            db.query(Youth)
            .join(Assignment, Assignment.youth_id == Youth.id)
            .filter(Assignment.professional_id == prof.id, Assignment.status == "ACTIVO")
        )
    elif user.role == "ADMIN":
        q = db.query(Youth)
    else:
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        youths = [youth] if youth else []
        q = None

    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50

    if q is not None:
        if is_active is not None:
            q = q.filter(Youth.is_active == is_active)
        if login_enabled is not None:
            q = q.filter(Youth.login_enabled == login_enabled)
        if search and search.strip():
            term = f"%{search.strip()}%"
            cleaned = re.sub(r"[^0-9kK]", "", search).upper()
            conditions = [
                Youth.display_name.ilike(term),
                Youth.identifier.ilike(term),
                Youth.rut.ilike(term),
            ]
            if cleaned:
                rut_norm = func.replace(func.replace(func.upper(Youth.rut), ".", ""), "-", "")
                conditions.append(rut_norm.ilike(f"%{cleaned}%"))
            q = q.filter(or_(*conditions))
        if use_pagination:
            total = q.order_by(None).count()
            if response:
                response.headers["X-Total-Count"] = str(total)
                response.headers["X-Page"] = str(page)
                response.headers["X-Page-Size"] = str(page_size)
            q = q.order_by(Youth.id.asc()).offset((page - 1) * page_size).limit(page_size)
        youths = q.order_by(Youth.id.asc()).all() if not use_pagination else q.all()
    elif use_pagination and response:
        response.headers["X-Total-Count"] = str(len(youths))
        response.headers["X-Page"] = str(page)
        response.headers["X-Page-Size"] = str(page_size)
    youth_ids = [y.id for y in youths]
    user_ids = [y.user_id for y in youths if y.user_id]
    last_session_map = _get_last_session_map(db, youth_ids)
    email_map = _get_user_email_map(db, user_ids)
    photo_map = _get_user_profile_photo_map(db, user_ids)

    result = []
    for y in youths:
        last_sess = last_session_map.get(y.id)
        status_label = "Con sesiones" if last_sess else "Sin sesiones"
        last_session = None
        if last_sess:
            last_session = LastSessionInfo(
                id=last_sess.id,
                started_at=last_sess.started_at,
                status=last_sess.status,
                ended_at=last_sess.ended_at,
            )
        email = email_map.get(y.user_id) if y.user_id else None
        profile_photo_url = photo_map.get(y.user_id) if y.user_id else None
        final_photo_url = y.photo_url or profile_photo_url
        result.append(
            YouthWithLastSession(
                id=y.id,
                user_id=y.user_id,
                display_name=y.display_name,
                identifier=y.identifier,
                rut=y.rut,
                email=email,
                profile_photo_url=final_photo_url,
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


class YouthLookupRequest(BaseModel):
    ids: list[int]


@router.post("/lookup")
def lookup_youths(
    data: YouthLookupRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Lookup rápido de nombres por ID, respetando permisos."""
    ids = list({i for i in data.ids if isinstance(i, int) or (isinstance(i, str) and str(i).isdigit())})
    ids = [int(i) for i in ids if int(i) > 0]
    if not ids:
        return []

    q = db.query(Youth.id, Youth.display_name, Youth.rut, Youth.user_id, Youth.photo_url).filter(Youth.id.in_(ids))
    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        if not youth or youth.id not in ids:
            return []
        q = q.filter(Youth.id == youth.id)
    elif user.role == "PROFESIONAL":
        from app.models.professional import Professional
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof:
            return []
        q = q.join(Assignment, Assignment.youth_id == Youth.id).filter(
            Assignment.professional_id == prof.id,
            Assignment.status == "ACTIVO",
        )
    elif user.role != "ADMIN":
        return []

    rows = q.all()
    user_ids = [r[3] for r in rows if r[3]]
    photo_map = _get_user_profile_photo_map(db, user_ids)
    return [
        {
            "id": r[0],
            "display_name": r[1],
            "rut": r[2],
            "profile_photo_url": r[4] or photo_map.get(r[3]),
        }
        for r in rows
    ]


@router.post("", response_model=YouthResponse)
def create_youth(
    data: YouthCreate,
    prof=Depends(get_current_professional),
    db: DBSession = Depends(get_db),
):
    """Crea joven y asignación automática. identifier lo genera el sistema. Si login_enabled+email: genera invitación."""
    profile_checklist_json = json.dumps(data.profile_checklist) if data.profile_checklist else None
    email = None
    if data.login_enabled and data.email:
        email = data.email.lower().strip()
        if not email:
            raise HTTPException(status_code=400, detail="Correo inválido")
        existing = db.query(User).filter(User.email.ilike(email)).first()
        if existing:
            raise HTTPException(status_code=409, detail="El correo ya está registrado")
    normalized_rut = None
    if data.rut:
        normalized_rut = _normalize_rut(data.rut)
        existing_rut = db.query(Youth).filter(Youth.rut == normalized_rut).first()
        if existing_rut:
            raise HTTPException(status_code=409, detail="El RUT ya está registrado")
    youth = _create_youth_with_unique_identifier(
        db,
        display_name=data.display_name,
        rut=normalized_rut,
        phone=data.phone,
        year_of_birth=data.year_of_birth,
        diagnosis=data.diagnosis,
        login_enabled=data.login_enabled,
        general_notes=data.general_notes,
        profile_checklist_json=profile_checklist_json,
    )
    db.add(Assignment(youth_id=youth.id, professional_id=prof.id, status="ACTIVO"))
    db.flush()
    activation_url = None
    if data.login_enabled and email:
        token = str(uuid.uuid4())
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        db.add(YouthInvitation(youth_id=youth.id, email=email, token=token, expires_at=expires))
        from app.config import settings
        activation_url = f"{settings.APP_BASE_URL}/activar?token={token}"
    db.commit()
    return _youth_to_response(youth, activation_url)


def _get_youth_email(db: DBSession, user_id: int) -> str | None:
    """Obtiene el email del User cuando user_id existe."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        return None
    return user.email


def _get_user_profile_photo(db: DBSession, user_id: int) -> str | None:
    """Obtiene profile_photo_url del User cuando user_id existe."""
    user = db.query(User).filter(User.id == user_id).first()
    return user.profile_photo_url if user else None


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
    profile_photo_url = _get_user_profile_photo(db, youth.user_id) if youth.user_id else None
    return _youth_to_response(youth, email=email, profile_photo_url=profile_photo_url)


@router.post("/{youth_id}/photo", response_model=YouthResponse)
def upload_youth_photo(
    youth_id: int,
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Sube foto del joven (profesional asignado o el propio joven)."""
    youth = db.query(Youth).filter(Youth.id == youth_id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")

    if user.role == "PROFESIONAL":
        from app.models.professional import Professional
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof:
            raise HTTPException(status_code=403, detail="Acceso denegado")
        assign = db.query(Assignment).filter(
            Assignment.youth_id == youth_id,
            Assignment.professional_id == prof.id,
            Assignment.status == "ACTIVO",
        ).first()
        if not assign:
            raise HTTPException(status_code=403, detail="Acceso denegado")
    elif user.role == "JOVEN":
        if youth.user_id != user.id:
            raise HTTPException(status_code=403, detail="Acceso denegado")
    elif user.role == "ADMIN":
        pass
    else:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo vacío")
    ext = Path(file.filename).suffix.lower()
    if ext not in YOUTH_PHOTO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Permitidas: {', '.join(sorted(YOUTH_PHOTO_EXTENSIONS))}",
        )

    _ensure_youth_photo_dir()
    unique_name = f"youth_{youth_id}_{uuid.uuid4().hex}{ext}"
    file_path = YOUTH_PHOTO_DIR / unique_name
    try:
        _save_youth_photo_stream(file, file_path)
    except HTTPException:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise
    except OSError as e:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    # Limpia foto anterior si estaba en /uploads/youths
    if youth.photo_url and "/uploads/youths/" in youth.photo_url:
        try:
            old_name = youth.photo_url.split("/uploads/youths/")[-1]
            old_path = YOUTH_PHOTO_DIR / old_name
            if old_path.exists():
                old_path.unlink(missing_ok=True)
        except Exception:
            pass

    base = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    youth.photo_url = f"{base}/uploads/youths/{unique_name}"
    db.commit()
    db.refresh(youth)
    email = _get_youth_email(db, youth.user_id) if youth.user_id else _get_pending_invitation_email(db, youth.id)
    profile_photo_url = _get_user_profile_photo(db, youth.user_id) if youth.user_id else None
    return _youth_to_response(youth, email=email, profile_photo_url=profile_photo_url)


@router.get("/{youth_id}/platform-sessions", response_model=list[PlatformSessionResponse])
def list_youth_platform_sessions(
    youth_id: int,
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
    response: Response = None,
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
    q = db.query(PlatformSession).filter(PlatformSession.user_id == youth.user_id)
    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50
        total = q.order_by(None).count()
        if response:
            response.headers["X-Total-Count"] = str(total)
            response.headers["X-Page"] = str(page)
            response.headers["X-Page-Size"] = str(page_size)
        q = q.order_by(desc(PlatformSession.started_at)).offset((page - 1) * page_size).limit(page_size)
    sessions = q.order_by(desc(PlatformSession.started_at)).all() if not use_pagination else q.all()
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
    prev_login_enabled = youth.login_enabled
    update_data = data.model_dump(exclude_unset=True)
    update_data.pop("identifier", None)  # no editable
    email = update_data.pop("email", None)
    profile_checklist = update_data.pop("profile_checklist", None)
    if "rut" in update_data:
        raw_rut = update_data.get("rut")
        if raw_rut:
            normalized_rut = _normalize_rut(raw_rut)
            existing_rut = db.query(Youth).filter(Youth.rut == normalized_rut, Youth.id != youth_id).first()
            if existing_rut:
                raise HTTPException(status_code=409, detail="El RUT ya está registrado")
            update_data["rut"] = normalized_rut
        else:
            update_data["rut"] = None
    for k, v in update_data.items():
        setattr(youth, k, v)
    if profile_checklist is not None:
        youth.profile_checklist = json.dumps(profile_checklist) if profile_checklist else None
    if "login_enabled" in update_data and update_data["login_enabled"] is False and prev_login_enabled:
        _disable_youth_login(db, youth)
    activation_url = None
    if youth.login_enabled and not youth.user_id and email:
        email = email.lower().strip()
        if not email:
            raise HTTPException(status_code=400, detail="Correo inválido")
        existing = db.query(User).filter(User.email.ilike(email)).first()
        if existing:
            raise HTTPException(status_code=409, detail="El correo ya está registrado")
        token = str(uuid.uuid4())
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        db.add(YouthInvitation(youth_id=youth.id, email=email, token=token, expires_at=expires))
        from app.config import settings
        activation_url = f"{settings.APP_BASE_URL}/activar?token={token}"
    db.commit()
    db.refresh(youth)
    email = _get_youth_email(db, youth.user_id) if youth.user_id else None
    profile_photo_url = _get_user_profile_photo(db, youth.user_id) if youth.user_id else None
    return _youth_to_response(youth, activation_url=activation_url, email=email, profile_photo_url=profile_photo_url)


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
    profile_photo_url = _get_user_profile_photo(db, youth.user_id) if youth.user_id else None
    return _youth_to_response(youth, email=email, profile_photo_url=profile_photo_url)


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
        raise HTTPException(status_code=400, detail="Correo inválido")
    existing = db.query(User).filter(User.email.ilike(new_email)).first()
    if existing and (not youth.user_id or existing.id != youth.user_id):
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    now = datetime.now(timezone.utc)
    (
        db.query(YouthInvitation)
        .filter(YouthInvitation.youth_id == youth.id, YouthInvitation.used_at.is_(None))
        .update({"used_at": now}, synchronize_session=False)
    )

    token = str(uuid.uuid4())
    expires = now + timedelta(days=7)
    db.add(YouthInvitation(youth_id=youth.id, email=new_email, token=token, expires_at=expires))
    from app.config import settings
    activation_url = f"{settings.APP_BASE_URL}/activar?token={token}"
    db.commit()
    db.refresh(youth)
    email = _get_youth_email(db, youth.user_id) if youth.user_id else None
    profile_photo_url = _get_user_profile_photo(db, youth.user_id) if youth.user_id else None
    return _youth_to_response(youth, activation_url=activation_url, email=email, profile_photo_url=profile_photo_url)


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
    profile_photo_url = _get_user_profile_photo(db, youth.user_id) if youth.user_id else None
    return _youth_to_response(youth, email=email, profile_photo_url=profile_photo_url)


@router.get("/{youth_id}/notifications", response_model=list[YouthNotificationResponse])
def list_youth_notifications(
    youth_id: int,
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    unread_only: bool | None = Query(None),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
    response: Response = None,
):
    """Lista notificaciones del joven. JOVEN: solo propias. PROFESIONAL: si asignado. ADMIN: todo."""
    if not _check_youth_access(db, user, youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")

    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 20

    q = db.query(YouthNotification).filter(YouthNotification.youth_id == youth_id)
    if unread_only:
        q = q.filter(YouthNotification.read_at.is_(None))

    total = q.order_by(None).count()
    unread_total = (
        db.query(YouthNotification)
        .filter(YouthNotification.youth_id == youth_id, YouthNotification.read_at.is_(None))
        .count()
    )

    if response:
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Total-Unread"] = str(unread_total)
        response.headers["X-Page"] = str(page or 1)
        response.headers["X-Page-Size"] = str(page_size or total)

    q = q.order_by(YouthNotification.created_at.desc(), YouthNotification.id.desc())
    if use_pagination:
        q = q.offset((page - 1) * page_size).limit(page_size)

    return q.all()


@router.patch("/{youth_id}/notifications/read")
def mark_notifications_read(
    youth_id: int,
    data: NotificationReadRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Marca notificaciones como leídas (por IDs)."""
    if not _check_youth_access(db, user, youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if not data.ids:
        return {"updated": 0}
    now = datetime.now(timezone.utc)
    updated = (
        db.query(YouthNotification)
        .filter(YouthNotification.youth_id == youth_id, YouthNotification.id.in_(data.ids))
        .update({"read_at": now}, synchronize_session=False)
    )
    db.commit()
    return {"updated": updated}


@router.patch("/{youth_id}/notifications/read-all")
def mark_all_notifications_read(
    youth_id: int,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Marca todas las notificaciones del joven como leídas."""
    if not _check_youth_access(db, user, youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    now = datetime.now(timezone.utc)
    updated = (
        db.query(YouthNotification)
        .filter(YouthNotification.youth_id == youth_id, YouthNotification.read_at.is_(None))
        .update({"read_at": now}, synchronize_session=False)
    )
    db.commit()
    return {"updated": updated}


