export interface SessionAudio {
  id: string;
  session_id: string;
  url: string;
  content_type?: string;
  file_size_bytes?: number;
  duration_seconds?: number;
  created_at: string;
  updated_at: string;
}
