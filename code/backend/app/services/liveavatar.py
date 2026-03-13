"""Integración con LiveAvatar (Context Dinámico)."""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.models.job_role import JobRole
from app.models.case import Case
from app.models.simulation_template import SimulationTemplate
from app.services.prompt_builder import build_prompt


DEFAULT_OPENING_TEXT = "Hola, soy Javiera y estaré a cargo de esta entrevista."
INVALID_LIVEAVATAR_IDS = {"", "default", "avatar-default", "voice-default", "ctx-elvir-dinamico"}


class LiveAvatarError(Exception):
    """Error en integración con LiveAvatar."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code or 502
        super().__init__(message)


def _extract_error_detail(resp: httpx.Response) -> str:
    """Extrae mensaje de error del body de LiveAvatar."""
    try:
        data = resp.json()
        if isinstance(data, dict):
            msg = data.get("message") or data.get("detail")
            if msg:
                return str(msg)
            if "detail" in data and isinstance(data["detail"], list):
                parts = [str(d.get("msg", d)) for d in data["detail"] if isinstance(d, dict)]
                if parts:
                    return "; ".join(parts)
    except Exception:
        pass
    return resp.text[:200] if resp.text else ""


def _headers(request_id: str | None = None) -> dict:
    headers = {
        "X-API-KEY": settings.LIVEAVATAR_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if request_id:
        headers["X-Request-ID"] = request_id
    return headers


def _normalize_id(value: str | None) -> str:
    return (value or "").strip()


def _is_valid_id(value: str | None) -> bool:
    v = _normalize_id(value)
    return bool(v) and v not in INVALID_LIVEAVATAR_IDS


def resolve_liveavatar_ids(template: SimulationTemplate) -> tuple[str | None, str | None, str | None]:
    """Resuelve IDs finales considerando overrides en .env."""
    return (
        settings.LIVEAVATAR_CONTEXT_ID or template.liveavatar_context_id,
        settings.LIVEAVATAR_AVATAR_ID or template.liveavatar_avatar_id,
        settings.LIVEAVATAR_VOICE_ID or template.liveavatar_voice_id,
    )


def get_liveavatar_config_status(template: SimulationTemplate) -> dict[str, bool]:
    """Valida si la configuracion efectiva es utilizable (sin marcadores de posicion)."""
    context_id, avatar_id, voice_id = resolve_liveavatar_ids(template)
    return {
        "api_key": bool(settings.LIVEAVATAR_API_KEY),
        "context_id": _is_valid_id(context_id),
        "avatar_id": _is_valid_id(avatar_id),
        "voice_id": _is_valid_id(voice_id),
    }


def is_liveavatar_configured(template: SimulationTemplate) -> bool:
    status = get_liveavatar_config_status(template)
    return all(status.values())


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    reraise=True,
)
def _patch_context(client: httpx.Client, url: str, body: dict, request_id: str | None = None) -> httpx.Response:
    """PATCH al contexto con reintentos en errores 5xx y tiempo de espera."""
    resp = client.patch(url, headers=_headers(request_id), json=body)
    if resp.status_code >= 500:
        resp.raise_for_status()
    return resp


def start_liveavatar_session(
    job_role: JobRole,
    case: Case,
    template: SimulationTemplate,
    request_id: str | None = None,
) -> dict:
    """
    Arma el prompt, actualiza el contexto en LiveAvatar y crea la sesión.
    Usa IDs de la plantilla con fallback a .env.
    Retorna: { session_id, livekit_url, access_token, max_session_duration }
    """
    # .env tiene prioridad; marcadores de posicion no son validos para LiveAvatar
    context_id, avatar_id, voice_id = resolve_liveavatar_ids(template)

    if not settings.LIVEAVATAR_API_KEY:
        raise LiveAvatarError("LIVEAVATAR_API_KEY no configurada", 503)
    if not _is_valid_id(context_id):
        raise LiveAvatarError("LIVEAVATAR_CONTEXT_ID no configurado o invalido", 503)
    if not _is_valid_id(avatar_id):
        raise LiveAvatarError("LIVEAVATAR_AVATAR_ID no configurado o invalido", 503)
    if not _is_valid_id(voice_id):
        raise LiveAvatarError("LIVEAVATAR_VOICE_ID no configurado o invalido", 503)

    prompt = build_prompt(job_role, case)
    opening_text = getattr(case, "opening_text", None) or DEFAULT_OPENING_TEXT
    base_url = settings.LIVEAVATAR_API_BASE.rstrip("/")

    try:
        with httpx.Client(timeout=30.0) as client:
            # 1. PATCH contexto (con reintentos en 5xx/tiempo de espera)
            patch_url = f"{base_url}/contexts/{context_id}"
            patch_body = {
                "name": "elvir_context_dinamico",
                "prompt": prompt,
                "opening_text": opening_text,
            }
            try:
                patch_resp = _patch_context(client, patch_url, patch_body, request_id=request_id)
            except httpx.HTTPStatusError as e:
                detail = _extract_error_detail(e.response)
                if e.response.status_code == 401:
                    raise LiveAvatarError("Credenciales LiveAvatar inválidas", 401)
                if e.response.status_code == 404:
                    raise LiveAvatarError("Contexto no encontrado en LiveAvatar", 404)
                if e.response.status_code == 422:
                    raise LiveAvatarError(f"LiveAvatar validación: {detail}", 422)
                if e.response.status_code >= 400:
                    raise LiveAvatarError(
                        f"Error LiveAvatar PATCH: {detail or str(e.response.status_code)}",
                        e.response.status_code,
                    )
                raise

            if patch_resp.status_code >= 400:
                detail = _extract_error_detail(patch_resp)
                raise LiveAvatarError(
                    f"Error al actualizar contexto: {detail or patch_resp.status_code}",
                    patch_resp.status_code,
                )

            # 2. POST a sessions/token
            token_resp = client.post(
                f"{base_url}/sessions/token",
                headers=_headers(request_id),
                json={
                    "mode": "FULL",
                    "avatar_id": avatar_id,
                    "avatar_persona": {
                        "language": "es",
                        "voice_id": voice_id,
                        "context_id": context_id,
                    },
                },
            )
            if token_resp.status_code == 401:
                raise LiveAvatarError("Credenciales LiveAvatar inválidas", 401)
            if token_resp.status_code >= 400:
                detail = _extract_error_detail(token_resp)
                raise LiveAvatarError(
                    f"LiveAvatar token: {detail or token_resp.status_code}",
                    token_resp.status_code,
                )
            token_data = token_resp.json()
            session_token = token_data.get("data", {}).get("session_token")
            if not session_token:
                raise LiveAvatarError("LiveAvatar no retornó session_token", 502)

            # 3. POST a sessions/start
            start_resp = client.post(
                f"{base_url}/sessions/start",
                headers={
                    "Authorization": f"Bearer {session_token}",
                    "Content-Type": "application/json",
                    **({"X-Request-ID": request_id} if request_id else {}),
                },
            )
            if start_resp.status_code >= 400:
                detail = _extract_error_detail(start_resp)
                raise LiveAvatarError(
                    f"LiveAvatar start: {detail or start_resp.status_code}",
                    start_resp.status_code,
                )
            start_data = start_resp.json()
            s = start_data.get("data", {})

            return {
                "session_id": s.get("session_id"),
                "livekit_url": s.get("livekit_url"),
                "access_token": s.get("livekit_client_token"),
                "max_session_duration": s.get("max_session_duration"),
            }

    except httpx.TimeoutException:
        raise LiveAvatarError("Timeout al conectar con LiveAvatar", 504)
    except LiveAvatarError:
        raise
    except httpx.HTTPStatusError as e:
        detail = _extract_error_detail(e.response)
        raise LiveAvatarError(
            f"Error LiveAvatar: {detail or e.response.status_code}",
            e.response.status_code,
        )
    except Exception as e:
        raise LiveAvatarError(f"Error inesperado LiveAvatar: {str(e)}", 502)


def get_session_transcript(liveavatar_session_id: str, request_id: str | None = None) -> dict | None:
    """
    Obtiene la transcripción de una sesión desde LiveAvatar.
    Retorna el dict con session_active, transcript_data (o None si falla).
    No lanza excepción; retorna None en caso de error (404, tiempo de espera, etc.).
    """
    if not liveavatar_session_id or not settings.LIVEAVATAR_API_KEY:
        return None
    base_url = settings.LIVEAVATAR_API_BASE.rstrip("/")
    url = f"{base_url}/sessions/{liveavatar_session_id}/transcript"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=_headers(request_id))
            if resp.status_code != 200:
                return None
            data = resp.json()
            inner = data.get("data") if isinstance(data, dict) else None
            if not inner or "transcript_data" not in inner:
                return None
            return {
                "session_active": inner.get("session_active"),
                "transcript_data": inner.get("transcript_data", []),
            }
    except Exception:
        return None

