"""Contexto de petición HTTP para correlación en logs (request_id)."""

from __future__ import annotations

from contextvars import ContextVar

current_request_id: ContextVar[str | None] = ContextVar("current_request_id", default=None)
