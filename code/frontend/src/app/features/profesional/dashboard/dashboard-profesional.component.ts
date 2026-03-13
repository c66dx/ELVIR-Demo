import { Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Observable, forkJoin } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';
import { ApiService } from '../../../core/services/api.service';
import { StatusBadgeComponent } from '../../../shared/status-badge/status-badge.component';
import type { Session } from '../../../core/models/session.model';
import { formatDate, formatDuration } from '../../../shared/utils/date-format.util';

export interface RecentSessionWithYouth extends Session {
  youthName: string;
  youthRut?: string;
  youthPhotoUrl?: string;
}

export interface DashboardProfesionalData {
  youthsCount: number;
  activeYouthsCount: number;
  sessionsCount: number;
  completedSessionsCount: number;
  recentSessions: RecentSessionWithYouth[];
}

/** Dashboard del profesional: conteo de jóvenes, sesiones y últimas simulaciones. */
@Component({
  selector: 'app-dashboard-profesional',
  standalone: true,
  imports: [AsyncPipe, RouterLink, StatusBadgeComponent],
  templateUrl: './dashboard-profesional.component.html',
  styleUrl: './dashboard-profesional.component.scss',
})
export class DashboardProfesionalComponent {
  private api = inject(ApiService);

  data$: Observable<DashboardProfesionalData> = forkJoin({
    youthsMeta: this.api.getYouthsPaged({ page: 1, page_size: 1 }),
    activeMeta: this.api.getYouthsPaged({ page: 1, page_size: 1, is_active: true }),
    sessionsPage: this.api.getSessionsPaged({ page: 1, page_size: 8 }),
    stats: this.api.getSessionStats({ months: 6 }),
  }).pipe(
    switchMap(({ youthsMeta, activeMeta, sessionsPage, stats }) => {
      const youthIds = Array.from(new Set(sessionsPage.items.map((s) => s.youth_id)));
      return this.api.getYouthLookup(youthIds).pipe(
        map((lookup) => {
          const youthMap = new Map(lookup.map((y) => [y.id, y]));
          const recent = sessionsPage.items.map((s) => ({
            ...s,
            youthName: youthMap.get(s.youth_id)?.display_name ?? 'Desconocido',
            youthRut: youthMap.get(s.youth_id)?.rut,
            youthPhotoUrl: youthMap.get(s.youth_id)?.profile_photo_url,
          }));
          return {
            youthsCount: youthsMeta.total,
            activeYouthsCount: activeMeta.total,
            sessionsCount: stats.total,
            completedSessionsCount: stats.completed,
            recentSessions: recent,
          };
        })
      );
    })
  );

  readonly formatDate = formatDate;
  readonly formatDuration = formatDuration;

  initials(name?: string | null): string {
    if (!name) return 'J';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return 'J';
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
}

