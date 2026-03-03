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
import { formatDate, formatDuration, formatStatusLabel } from '../../../shared/utils/date-format.util';

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

  readonly formatDate = formatDate;
  readonly formatDuration = formatDuration;

  formatStatus(status: SessionStatus | undefined): string {
    return status ? formatStatusLabel(status) : '-';
  }
}
