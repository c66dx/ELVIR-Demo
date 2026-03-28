"""Esquemas Pydantic del panel de administración."""
from datetime import datetime

from pydantic import BaseModel


class AdminAssignedProfessional(BaseModel):
    id: int
    display_name: str
    email: str | None = None
    is_active: bool


class AdminYouthRow(BaseModel):
    id: int
    user_id: int | None = None
    display_name: str
    identifier: str | None = None
    rut: str | None = None
    email: str | None = None
    profile_photo_url: str | None = None
    login_enabled: bool
    is_active: bool
    login_type: str
    last_login_at: datetime | None = None
    last_interview_at: datetime | None = None
    last_interview_status: str | None = None
    last_interview_mode: str | None = None
    assigned_professional: AdminAssignedProfessional | None = None


class AdminProfessionalRow(BaseModel):
    id: int
    user_id: int
    display_name: str
    email: str | None = None
    profile_photo_url: str | None = None
    is_active: bool
    login_type: str
    last_login_at: datetime | None = None


class AdminListMeta(BaseModel):
    total: int
    page: int
    page_size: int


class AdminUsersOverviewMeta(BaseModel):
    youths: AdminListMeta | None = None
    professionals: AdminListMeta | None = None


class AdminUsersOverviewResponse(BaseModel):
    youths: list[AdminYouthRow]
    professionals: list[AdminProfessionalRow]
    meta: AdminUsersOverviewMeta | None = None


class AdminPlatformLogItem(BaseModel):
    started_at: datetime
    ended_at: datetime | None = None


class AdminInterviewLogItem(BaseModel):
    id: int
    started_at: datetime
    ended_at: datetime | None = None
    status: str
    mode: str
    professional_id: int | None = None
    professional_name: str | None = None


class AdminYouthLogsMeta(BaseModel):
    platform: AdminListMeta | None = None
    interviews: AdminListMeta | None = None


class AdminYouthLogsResponse(BaseModel):
    platform_sessions: list[AdminPlatformLogItem]
    interviews: list[AdminInterviewLogItem]
    meta: AdminYouthLogsMeta | None = None


class AuditLogRow(BaseModel):
    id: int
    request_id: str | None = None
    actor_user_id: int | None = None
    actor_role: str | None = None
    actor_email: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    status_code: int
    method: str
    path: str
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRow]
    meta: AdminListMeta
