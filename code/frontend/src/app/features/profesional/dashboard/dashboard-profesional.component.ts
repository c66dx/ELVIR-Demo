import { Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Observable } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';
import { ApiService } from '../../../core/services/api.service';
import { StatusBadgeComponent } from '../../../shared/status-badge/status-badge.component';
import type { Session } from '../../../core/models/session.model';

export interface RecentSessionWithYouth extends Session {
  youthName: string;
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

  data$: Observable<DashboardProfesionalData> = this.api.getYouths().pipe(
    switchMap((youths) =>
      this.api.getSessions().pipe(
        map((sessions) => {
          const youthMap = new Map(youths.map((y) => [y.id, y.display_name]));
          const sorted = [...sessions].sort((a, b) => (b.started_at > a.started_at ? 1 : -1));
          const recent = sorted.slice(0, 8).map((s) => ({
            ...s,
            youthName: youthMap.get(s.youth_id) ?? 'Desconocido',
          }));
          const completed = sessions.filter((s) => s.status === 'COMPLETADA').length;
          const activeYouths = youths.filter((y) => y.is_active).length;
          return {
            youthsCount: youths.length,
            activeYouthsCount: activeYouths,
            sessionsCount: sessions.length,
            completedSessionsCount: completed,
            recentSessions: recent,
          };
        })
      )
    )
  );

  formatDate(iso?: string): string {
    if (!iso) return '-';
    return new Date(iso).toLocaleDateString('es-CL', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  formatDuration(seconds?: number): string {
    if (!seconds) return '-';
    const m = Math.floor(seconds / 60);
    return m > 0 ? `${m} min` : `${seconds} s`;
  }
}
