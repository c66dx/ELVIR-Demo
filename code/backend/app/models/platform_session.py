"""Modelo PLATFORM_SESSIONS - Registro de entrada/salida a la plataforma web.

Diferente de SESSIONS (simulaciones de entrevista). Sirve para métricas:
- Cuándo el usuario entró a la plataforma (login)
- Cuándo cerró sesión (logout)
"""

from sqlalchemy import Column, DateTime, Integer, ForeignKey, func

from app.database import Base


class PlatformSession(Base):
    __tablename__ = "platform_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)  # nulo = sesion activa

