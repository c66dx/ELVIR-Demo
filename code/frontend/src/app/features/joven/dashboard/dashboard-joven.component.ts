import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Observable, of, forkJoin } from 'rxjs';
import { switchMap, map } from 'rxjs/operators';
import { YouthService } from '@core/services/youth.service';
import { MaterialApiService } from '@core/services/material-api.service';
import { SessionApiService } from '@core/services/session-api.service';
import { StatusBadgeComponent } from '@shared/status-badge/status-badge.component';
import type { Session } from '@core/models/session.model';
import type { SessionStatus } from '@core/models/types.model';
import { formatDate, formatDuration, formatStatusLabel } from '@shared/utils/date-format.util'; 
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
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DashboardJovenComponent { 
 private youthService = inject(YouthService); 
 private materialsApi = inject(MaterialApiService); 
 private sessionsApi = inject(SessionApiService); 
 data$: Observable<DashboardJovenData> = this.youthService.getCurrentYouthId().pipe(   switchMap((youthId) => { 
 if (!youthId) return of(this.emptyData()); 
 return forkJoin({ 
 sessionsPage: this.sessionsApi.getSessionsPaged({ youth_id: youthId, page: 1, page_size: 5 }),   stats: this.sessionsApi.getSessionStats({ youth_id: youthId, months: 6 }),   suggestionsMeta: this.materialsApi.getYouthMaterialSuggestionsPaged(youthId, { page: 1, page_size: 1 }),   }).pipe(   map(({ sessionsPage, stats, suggestionsMeta }) => { 
 const sorted = [...sessionsPage.items].sort((a, b) => (b.started_at > a.started_at ? 1 : -1)); 
 return { 
 totalSessions: stats.total,   completedSessions: stats.completed,   lastSession: sorted[0] ?? null,   recentSessions: sorted.slice(0, 5),   materialSuggestionsCount: suggestionsMeta.total,   }; 
 })   ); 
 })   ); 
 private emptyData(): DashboardJovenData { 
 return { 
 totalSessions: 0,   completedSessions: 0,   lastSession: null,   recentSessions: [],   materialSuggestionsCount: 0,   }; 
 } 
 readonly formatDate = formatDate; 
 readonly formatDuration = formatDuration; 
 formatStatus(status: SessionStatus | undefined): string { 
 return status ?  formatStatusLabel(status) : '-'; 
 }
}



