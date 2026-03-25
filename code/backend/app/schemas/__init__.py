"""Paquete de esquemas Pydantic.

Este módulo evita imports ansiosos para no forzar dependencias de todos
los esquemas cuando solo se necesita uno específico.

Uso recomendado:
    from app.schemas.session import SessionCreate
    from app.schemas.auth import LoginRequest
"""

__all__: list[str] = []

