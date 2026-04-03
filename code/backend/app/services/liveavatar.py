"""Integración con LiveAvatar (Context Dinámico)."""

import logging

import httpx

logger = logging.getLogger("elvir.api")
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.case import Case
from app.models.job_role import JobRole
from app.models.simulation_template import SimulationTemplate
from app.schemas.prompt import PromptInput
from app.services.prompt_engine import PromptProviderError, get_prompt

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


def describe_liveavatar_config_gaps(template: SimulationTemplate) -> str:
    """
    Texto para la UI cuando falta API key o IDs (sin exponer secretos).
    Indica qué variable o campo corregir.
    """
    status = get_liveavatar_config_status(template)
    context_id, avatar_id, voice_id = resolve_liveavatar_ids(template)
    ctx = _normalize_id(context_id)
    av = _normalize_id(avatar_id)
    vo = _normalize_id(voice_id)

    gaps: list[str] = []
    if not status["api_key"]:
        gaps.append("añade LIVEAVATAR_API_KEY en code/backend/.env (clave de la API en el panel de LiveAvatar).")

    def _append_id_gap(field: str, env_name: str, value: str, ok: bool) -> None:
        if ok:
            return
        if not value:
            gaps.append(f"falta {field} válido: define {env_name} en .env o el ID en la plantilla de simulación (BD).")
        elif value in INVALID_LIVEAVATAR_IDS:
            gaps.append(
                f"{field} sigue siendo marcador de demo ({value}); sustitúyelo por un ID real del panel LiveAvatar."
            )
        else:
            gaps.append(f"{field} no es válido para esta integración.")

    _append_id_gap("context_id", "LIVEAVATAR_CONTEXT_ID", ctx, status["context_id"])
    _append_id_gap("avatar_id", "LIVEAVATAR_AVATAR_ID", av, status["avatar_id"])
    _append_id_gap("voice_id", "LIVEAVATAR_VOICE_ID", vo, status["voice_id"])

    if not gaps:
        return "LiveAvatar no configurado."
    head = "LiveAvatar no está configurado para esta simulación."
    return f"{head} " + " ".join(gaps)


def log_startup_env_hint() -> None:
    """Registra en arranque si las variables de .env permiten LiveAvatar (sin consultar BD)."""
    api_key = bool(settings.LIVEAVATAR_API_KEY)
    ctx_ok = _is_valid_id(settings.LIVEAVATAR_CONTEXT_ID)
    av_ok = _is_valid_id(settings.LIVEAVATAR_AVATAR_ID)
    vo_ok = _is_valid_id(settings.LIVEAVATAR_VOICE_ID)
    logger.info(
        "liveavatar .env: api_key=%s context_id_ok=%s avatar_id_ok=%s voice_id_ok=%s",
        api_key,
        ctx_ok,
        av_ok,
        vo_ok,
    )
    if not (api_key and ctx_ok and av_ok and vo_ok):
        logger.warning(
            "LiveAvatar: con el seed por defecto los IDs en BD son marcadores "
            "(ctx-elvir-dinamico, avatar-default, voice-default) y se rechazan. "
            "Define LIVEAVATAR_API_KEY, LIVEAVATAR_CONTEXT_ID, LIVEAVATAR_AVATAR_ID y "
            "LIVEAVATAR_VOICE_ID en code/backend/.env con valores reales del panel de LiveAvatar, "
            "luego reinicia el API. El archivo .env debe estar en code/backend/ (misma carpeta que app/)."
        )


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
    prompt_input: PromptInput | None = None,
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

    try:
        prompt_result = get_prompt(job_role, case, prompt_input=prompt_input, request_id=request_id)
    except PromptProviderError as e:
        raise LiveAvatarError(f"Prompt provider: {e}", 502)

    prompt = prompt_result.prompt
    opening_text = prompt_result.opening_text or getattr(case, "opening_text", None) or DEFAULT_OPENING_TEXT
    context_name = prompt_result.name or "elvir_context_dinamico"
    base_url = settings.LIVEAVATAR_API_BASE.rstrip("/")

    try:
        with httpx.Client(timeout=30.0) as client:
            # 1. PATCH contexto (con reintentos en 5xx/tiempo de espera)
            patch_url = f"{base_url}/contexts/{context_id}"
            patch_body = {
                "name": context_name,
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
            if not isinstance(token_data, dict):
                raise LiveAvatarError("LiveAvatar /sessions/token: respuesta JSON inválida", 502)
            td = token_data.get("data")
            if not isinstance(td, dict):
                td = token_data
            session_token = td.get("session_token") or td.get("token")
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
            if not isinstance(start_data, dict):
                raise LiveAvatarError("LiveAvatar /sessions/start: respuesta JSON inválida", 502)
            s = start_data.get("data")
            if not isinstance(s, dict):
                s = start_data
            livekit_url = s.get("livekit_url")
            access_token = s.get("livekit_client_token") or s.get("access_token") or s.get("livekit_token")
            if not livekit_url or not access_token:
                keys = list(s.keys()) if isinstance(s, dict) else []
                logger.warning(
                    "liveavatar /sessions/start incompleto: keys=%s livekit_url=%s token=%s",
                    keys[:20],
                    bool(livekit_url),
                    bool(access_token),
                )
                raise LiveAvatarError(
                    "LiveAvatar no devolvió livekit_url o token de cliente; "
                    f"revisa la versión de la API (keys en data: {keys[:15]})",
                    502,
                )

            return {
                "session_id": s.get("session_id"),
                "livekit_url": livekit_url,
                "access_token": access_token,
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
