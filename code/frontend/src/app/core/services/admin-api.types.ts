import type { SessionMode, SessionStatus } from '@core/models/types.model';

export interface AdminAssignedProfessional {
  id: string;
  display_name: string;
  email?: string;
  is_active: boolean;
}

export interface AdminYouthLogRow {
  id: string;
  user_id?: string;
  display_name: string;
  identifier?: string;
  rut?: string;
  email?: string;
  profile_photo_url?: string;
  login_enabled: boolean;
  is_active: boolean;
  login_type: string;
  last_login_at?: string;
  last_interview_at?: string;
  last_interview_status?: string;
  last_interview_mode?: string;
  assigned_professional?: AdminAssignedProfessional;
}

export interface AdminProfessionalLogRow {
  id: string;
  user_id: string;
  display_name: string;
  email?: string;
  profile_photo_url?: string;
  is_active: boolean;
  login_type: string;
  last_login_at?: string;
}

export interface AdminListMeta {
  total: number;
  page: number;
  page_size: number;
}

export interface AdminUsersOverviewMeta {
  youths?: AdminListMeta;
  professionals?: AdminListMeta;
}

export interface AdminUsersOverview {
  youths: AdminYouthLogRow[];
  professionals: AdminProfessionalLogRow[];
  meta?: AdminUsersOverviewMeta;
}

export interface AdminPlatformLogItem {
  started_at: string;
  ended_at?: string;
}

export interface AdminInterviewLogItem {
  id: string;
  started_at: string;
  ended_at?: string;
  status: SessionStatus;
  mode: SessionMode;
  professional_id?: string;
  professional_name?: string;
}

export interface AdminYouthLogs {
  platform_sessions: AdminPlatformLogItem[];
  interviews: AdminInterviewLogItem[];
  meta?: {
    platform?: AdminListMeta;
    interviews?: AdminListMeta;
  };
}

export interface AuditLogRow {
  id: string;
  request_id?: string;
  actor_user_id?: string;
  actor_role?: string;
  actor_email?: string;
  action: string;
  entity_type?: string;
  entity_id?: string;
  status_code: number;
  method: string;
  path: string;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}
