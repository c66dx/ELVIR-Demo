export interface TranscriptEntry {
  role: 'user' | 'avatar';
  transcript: string;
  absolute_timestamp: number;
  relative_timestamp: number;
}

export interface TranscriptResponse {
  transcript_data: TranscriptEntry[];
  session_active?: boolean;
  fetched_at?: string;
}
