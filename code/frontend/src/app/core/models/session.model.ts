import type { SessionStatus, SessionMode } from './types.model';

export interface Session {
  id: string;
  youth_id: string;
  professional_id?: string;
  simulation_template_id: string;
  mode: SessionMode;
  liveavatar_session_id?: string;
  started_at: string;
  ended_at?: string;
  status: SessionStatus;
  duration_seconds?: number;
  metrics?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}
