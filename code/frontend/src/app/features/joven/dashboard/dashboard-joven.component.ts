import { Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Observable, of } from 'rxjs';
import { switchMap, map } from 'rxjs/operators';
import { YouthService } from '../../../core/services/youth.service';
import { ApiService } from '../../../core/services/api.service';
import { StatusBadgeComponent } from '../../../shared/status-badge/status-badge.component';
import type { Session } from '../../../core/models/session.model';
import type { SessionStatus } from '../../../core/models/types.model';

export interface DashboardJovenData {
  totalSessions: number;
  completedSessions: number;
  lastSession: Session | null;
  recentSessions: Session[];
  materialSuggestionsCount: number;
}

/** Dashboard del joven: resumen de sesiones, última simulación, material sugerido, accesos rápidos. */
@Component({
  selector: 'app-dashboard-joven',
  standalone: true,
  imports: [AsyncPipe, RouterLink, StatusBadgeComponent],
  templateUrl: './dashboard-joven.component.html',
  styleUrl: './dashboard-joven.component.scss',
})
export class DashboardJovenComponent {
  private youthService = inject(YouthService);
  private api = inject(ApiService);

  data$: Observable<DashboardJovenData> = this.youthService.getCurrentYouthId().pipe(
    switchMap((youthId) => {
      if (!youthId) return of(this.emptyData());
      return this.api.getSessions({ youth_id: youthId }).pipe(
        switchMap((sessions) =>
          this.api.getYouthMaterialSuggestions(youthId).pipe(
            map((suggestions) => ({ sessions, suggestions }))
          )
        ),
        map(({ sessions, suggestions }) => {
          const sorted = [...sessions].sort((a, b) => (b.started_at > a.started_at ? 1 : -1));
          const completed = sessions.filter((s) => s.status === 'COMPLETADA').length;
          return {
            totalSessions: sessions.length,
            completedSessions: completed,
            lastSession: sorted[0] ?? null,
            recentSessions: sorted.slice(0, 5),
            materialSuggestionsCount: suggestions.length,
          };
        })
      );
    })
  );

  private emptyData(): DashboardJovenData {
    return {
      totalSessions: 0,
      completedSessions: 0,
      lastSession: null,
      recentSessions: [],
      materialSuggestionsCount: 0,
    };
  }

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

  formatStatus(status: SessionStatus | undefined): string {
    const labels: Record<string, string> = {
      EN_CURSO: 'En curso',
      COMPLETADA: 'Completada',
      CANCELADA: 'Cancelada',
      ERROR: 'Error',
    };
    return status ? labels[status] ?? status : '-';
  }

  formatDuration(seconds?: number): string {
    if (!seconds) return '-';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m} min` : `${s} s`;
  }
}
