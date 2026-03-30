"""Normalización y validación de RUT chileno."""

from __future__ import annotations

import re

from fastapi import HTTPException


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


def normalize_rut(value: str) -> str:
    """Valida dígito verificador y devuelve RUT formateado (XX.XXX.XXX-Y)."""
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
