"""Política de longitud de contraseñas (configurable por entorno)."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.config import settings


def min_password_length() -> int:
    return settings.PASSWORD_MIN_LENGTH


def raise_if_password_too_short(plain: str, *, field_label: str = "La contraseña") -> None:
    """HTTP 400 si plain (ya no vacío) no cumple la longitud mínima."""
    p = plain.strip()
    if len(p) < settings.PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_label} debe tener al menos {settings.PASSWORD_MIN_LENGTH} caracteres",
        )


def activation_password_error_code(password: str | None) -> str | None:
    """
    Si password tiene contenido pero es demasiado corta, devuelve código para ActivateResponse.
    Si está vacía o es None, devuelve None (el caller valida PASSWORD_REQUIRED).
    """
    if password is None or not str(password).strip():
        return None
    if len(password.strip()) < settings.PASSWORD_MIN_LENGTH:
        return "PASSWORD_TOO_SHORT"
    return None
