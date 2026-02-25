"""Integración con LiveAvatar (Context Dinámico)."""
import httpx

from app.config import settings
from app.models.job_role import JobRole
from app.models.case import Case
from app.services.prompt_builder import build_prompt


OPENING_TEXT = "Hola, soy Javiera y estaré a cargo de esta entrevista."


def _headers() -> dict:
    return {
        "X-API-KEY": settings.LIVEAVATAR_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def start_liveavatar_session(
    job_role: JobRole,
    case: Case,
) -> dict:
    """
    Arma el prompt, actualiza el contexto en LiveAvatar y crea la sesión.
    Retorna: { session_id, livekit_url, access_token, max_session_duration }
    """
    if not settings.LIVEAVATAR_API_KEY or not settings.LIVEAVATAR_CONTEXT_ID:
        raise ValueError(
            "LIVEAVATAR_API_KEY y LIVEAVATAR_CONTEXT_ID deben estar configurados en .env"
        )

    prompt = build_prompt(job_role, case)
    context_id = settings.LIVEAVATAR_CONTEXT_ID
    avatar_id = settings.LIVEAVATAR_AVATAR_ID or "default"
    voice_id = settings.LIVEAVATAR_VOICE_ID or "default"
    base_url = settings.LIVEAVATAR_API_BASE.rstrip("/")

    with httpx.Client(timeout=30.0) as client:
        # 1. PATCH contexto
        patch_resp = client.patch(
            f"{base_url}/contexts/{context_id}",
            headers=_headers(),
            json={
                "name": "elvir_context_dinamico",
                "prompt": prompt,
                "opening_text": OPENING_TEXT,
            },
        )
        patch_resp.raise_for_status()

        # 2. POST sessions/token
        token_resp = client.post(
            f"{base_url}/sessions/token",
            headers=_headers(),
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
        token_resp.raise_for_status()
        token_data = token_resp.json()
        session_token = token_data.get("data", {}).get("session_token")
        if not session_token:
            raise ValueError("LiveAvatar no retornó session_token")

        # 3. POST sessions/start
        start_resp = client.post(
            f"{base_url}/sessions/start",
            headers={
                "Authorization": f"Bearer {session_token}",
                "Content-Type": "application/json",
            },
        )
        start_resp.raise_for_status()
        start_data = start_resp.json()
        s = start_data.get("data", {})

        return {
            "session_id": s.get("session_id"),
            "livekit_url": s.get("livekit_url"),
            "access_token": s.get("livekit_client_token"),
            "max_session_duration": s.get("max_session_duration"),
        }
