"""Integracion robusta para prompt dinamico (endpoint o script).

Contrato esperado (minimo):
- POST /prompt/generate -> { "prompt": "...", "opening_text": "...", "name": "...", "version": "..." }
- POST /prompt/evaluate -> { "snapshot": { ... }, "version": "..." }
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess

import httpx

from app.config import settings
from app.schemas.prompt import EvaluationInput, EvaluationResult, PromptInput, PromptResult
from app.services.prompt_builder import build_prompt


class PromptProviderError(Exception):
    """Error al obtener prompt desde proveedor externo."""


def _endpoint_headers(request_id: str | None = None) -> dict:
    # Headers base + API key opcional (configurable por .env)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    api_key = (settings.PROMPT_ENDPOINT_API_KEY or "").strip()
    if api_key:
        header_name = (settings.PROMPT_ENDPOINT_API_KEY_HEADER or "Authorization").strip()
        prefix = (settings.PROMPT_ENDPOINT_API_KEY_PREFIX or "").strip()
        if prefix:
            headers[header_name] = f"{prefix} {api_key}"
        else:
            headers[header_name] = api_key
    if request_id:
        headers["X-Request-ID"] = request_id
    return headers


def _build_url(base: str, path: str) -> str:
    # Construye URL final a partir de base + path
    b = (base or "").strip().rstrip("/")
    p = (path or "").strip().lstrip("/")
    if not b:
        raise PromptProviderError("PROMPT_ENDPOINT_BASE no configurado")
    if not p:
        raise PromptProviderError("Ruta de endpoint no configurada")
    return f"{b}/{p}"


def _parse_cmd(raw_cmd: str) -> list[str]:
    if not raw_cmd or not raw_cmd.strip():
        raise PromptProviderError("Comando de script no configurado")
    # En Windows, posix=False maneja mejor las comillas.
    return shlex.split(raw_cmd, posix=os.name != "nt")


def _run_script(cmd: list[str], payload: dict, timeout_s: int) -> dict:
    try:
        proc = subprocess.run(
            cmd,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise PromptProviderError(f"Timeout ejecutando script: {e}") from e
    except Exception as e:
        raise PromptProviderError(f"Error ejecutando script: {e}") from e

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise PromptProviderError(f"Script retorno codigo {proc.returncode}: {stderr}")

    stdout = (proc.stdout or "").strip()
    if not stdout:
        raise PromptProviderError("Script no devolvio salida")

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise PromptProviderError(f"Salida no es JSON valido: {e}") from e


def get_prompt(
    job_role,
    case,
    prompt_input: PromptInput | None = None,
    request_id: str | None = None,
) -> PromptResult:
    provider = (settings.PROMPT_PROVIDER or "endpoint").strip().lower()
    prompt_input = prompt_input or PromptInput()

    if provider == "endpoint":
        # Llama al endpoint externo para obtener prompt dinamico
        url = settings.PROMPT_ENDPOINT_INTERVENIR_URL
        if not url:
            url = _build_url(settings.PROMPT_ENDPOINT_BASE, settings.PROMPT_ENDPOINT_INTERVENIR_PATH)

        payload = prompt_input.model_dump(exclude_none=True)
        try:
            with httpx.Client(timeout=settings.PROMPT_ENDPOINT_TIMEOUT_S) as client:
                resp = client.post(url, headers=_endpoint_headers(request_id), json=payload)
        except httpx.TimeoutException as e:
            raise PromptProviderError(f"Timeout llamando endpoint: {e}") from e
        except Exception as e:
            raise PromptProviderError(f"Error llamando endpoint: {e}") from e

        if resp.status_code >= 400:
            detail = resp.text[:200] if resp.text else ""
            raise PromptProviderError(f"Endpoint {resp.status_code}: {detail}")

        data = resp.json()
        prompt = data.get("prompt")
        if not prompt:
            raise PromptProviderError("Endpoint no devolvio 'prompt'")

        return PromptResult(
            prompt=prompt,
            opening_text=data.get("opening_text"),
            name=data.get("name"),
            provider="endpoint",
            version=data.get("version"),
            raw=data if settings.PROMPT_STORE_RAW else None,
        )

    if provider == "script":
        payload = prompt_input.model_dump(exclude_none=True)
        cmd = _parse_cmd(settings.PROMPT_SCRIPT_INTERVENIR_CMD)
        data = _run_script(cmd, payload, settings.PROMPT_SCRIPT_TIMEOUT_S)
        prompt = data.get("prompt")
        if not prompt:
            raise PromptProviderError("Script no devolvio 'prompt'")
        return PromptResult(
            prompt=prompt,
            opening_text=data.get("opening_text"),
            name=data.get("name"),
            provider="script",
            version=data.get("version"),
            raw=data if settings.PROMPT_STORE_RAW else None,
        )

    if provider == "local":
        # Fallback local si no hay endpoint
        prompt = build_prompt(job_role, case)
        name = None
        if job_role and case:
            name = f"{job_role.name} - {case.name}"
        return PromptResult(prompt=prompt, provider="local", name=name)

    raise PromptProviderError(f"Proveedor no soportado: {provider}")


def evaluate(
    eval_input: EvaluationInput,
    request_id: str | None = None,
) -> EvaluationResult:
    provider = (settings.PROMPT_PROVIDER or "endpoint").strip().lower()

    if provider == "endpoint":
        # Llama al endpoint externo para evaluar la transcripcion
        url = settings.PROMPT_ENDPOINT_EVALUAR_URL
        if not url:
            url = _build_url(settings.PROMPT_ENDPOINT_BASE, settings.PROMPT_ENDPOINT_EVALUAR_PATH)

        payload = eval_input.model_dump(exclude_none=True)
        try:
            with httpx.Client(timeout=settings.PROMPT_ENDPOINT_TIMEOUT_S) as client:
                resp = client.post(url, headers=_endpoint_headers(request_id), json=payload)
        except httpx.TimeoutException as e:
            raise PromptProviderError(f"Timeout llamando endpoint: {e}") from e
        except Exception as e:
            raise PromptProviderError(f"Error llamando endpoint: {e}") from e

        if resp.status_code >= 400:
            detail = resp.text[:200] if resp.text else ""
            raise PromptProviderError(f"Endpoint {resp.status_code}: {detail}")

        data = resp.json()
        return EvaluationResult(
            snapshot=data.get("snapshot"),
            provider="endpoint",
            version=data.get("version"),
            raw=data if settings.PROMPT_STORE_RAW else None,
        )

    if provider == "script":
        payload = eval_input.model_dump(exclude_none=True)
        cmd = _parse_cmd(settings.PROMPT_SCRIPT_EVALUAR_CMD)
        data = _run_script(cmd, payload, settings.PROMPT_SCRIPT_TIMEOUT_S)
        return EvaluationResult(
            snapshot=data.get("snapshot"),
            provider="script",
            version=data.get("version"),
            raw=data if settings.PROMPT_STORE_RAW else None,
        )

    if provider == "local":
        # No hay evaluador local implementado
        return EvaluationResult(snapshot=None, provider="local")

    raise PromptProviderError(f"Proveedor no soportado: {provider}")
