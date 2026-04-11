import type { Session } from '@core/models/session.model';
import type { Youth } from '@core/models/youth.model';

export interface PagedResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface SessionWithTemplateLabel extends Session {
  templateLabel?: string;
}

export interface PlatformSessionItem {
  id: string;
  user_id: string;
  started_at: string;
  ended_at?: string;
}

export type YouthNotificationType = 'material' | 'feedback' | 'session' | 'general';

export interface YouthNotificationDto {
  id: string;
  youth_id: string;
  type: YouthNotificationType;
  title: string;
  message: string;
  link?: string;
  entity_type?: string;
  entity_id?: string;
  created_at: string;
  read_at?: string | null;
}

export interface YouthNotificationsPage extends PagedResult<YouthNotificationDto> {
  unread: number;
}

export type CreateYouthResponse = Youth & { activation_url?: string };

export type UpdateYouthResponse = Youth & { activation_url?: string };

export interface YouthWithLastSession extends Youth {
  status_label?: string;
  last_session?: Pick<Session, 'id' | 'status' | 'started_at' | 'ended_at'>;
}
