export interface SessionEvent {
  id: string;
  session_id: string;
  event_type: string;
  occurred_at: string;
  payload?: Record<string, unknown>;
}
