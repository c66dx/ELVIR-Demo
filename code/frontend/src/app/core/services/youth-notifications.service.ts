import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { ApiService, type YouthNotificationDto } from './api.service';

export type YouthNotificationType = 'material' | 'feedback' | 'session' | 'general';

export interface YouthNotification {
  id: string;
  type: YouthNotificationType;
  title: string;
  message: string;
  time: string;
  createdAt: string;
  link?: string;
  read?: boolean;
}

export interface YouthNotificationsResult {
  items: YouthNotification[];
  total: number;
  unread: number;
  page: number;
  page_size: number;
}

@Injectable({ providedIn: 'root' })
export class YouthNotificationsService {
  private api = inject(ApiService);

  getYouthNotifications(
    youthId: string,
    params?: { page?: number; page_size?: number; unread_only?: boolean }
  ): Observable<YouthNotificationsResult> {
    return this.api.getYouthNotificationsPaged(youthId, params).pipe(
      map((paged) => ({
        ...paged,
        items: paged.items.map((item) => this.mapNotification(item)),
      }))
    );
  }

  markAsRead(youthId: string, id: string): Observable<{ updated: number }> {
    return this.api.markYouthNotificationsRead(youthId, [id]);
  }

  markAllRead(youthId: string): Observable<{ updated: number }> {
    return this.api.markAllYouthNotificationsRead(youthId);
  }

  private mapNotification(item: YouthNotificationDto): YouthNotification {
    const createdAt = item.created_at;
    return {
      id: item.id,
      type: item.type as YouthNotificationType,
      title: item.title,
      message: item.message,
      time: this.formatRelativeTime(createdAt),
      createdAt,
      link: item.link ?? undefined,
      read: !!item.read_at,
    };
  }

  private formatRelativeTime(isoDate: string): string {
    const date = new Date(isoDate);
    if (Number.isNaN(date.getTime())) return 'Reciente';
    const diffMs = Date.now() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'Hace un momento';
    if (diffMin < 60) return `Hace ${diffMin} min`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `Hace ${diffHours} h`;
    if (diffHours < 48) return 'Ayer';
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `Hace ${diffDays} dias`;
    return date.toLocaleDateString('es-CL', { day: '2-digit', month: 'short' });
  }
}
