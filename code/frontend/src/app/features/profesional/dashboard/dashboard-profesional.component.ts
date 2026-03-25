import { Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Observable, forkJoin, of } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';
import { ApiService } from '../../../core/services/api.service';
import type { Session } from '../../../core/models/session.model';
import type { Youth } from '../../../core/models/youth.model';
import type { SessionWithTemplateLabel } from '../../../core/services/api.service';
import { StatusBadgeComponent } from '../../../shared/status-badge/status-badge.component';
import { formatDate } from '../../../shared/utils/date-format.util'; 
 export interface DashboardSessionItem { 
 id: string; 
 youthId: string; 
 youthName: string; 
 youthRut?: string; 
 youthPhotoUrl?: string; 
 status: Session['status']; 
 mode: Session['mode']; 
 started_at: string; 
 templateLabel?: string; 
 pendingFeedback?: boolean;
} 
 export interface DashboardProfesionalData { 
 pendingSessions: DashboardSessionItem[]; 
 inProgressSessions: DashboardSessionItem[]; 
 completedSessions: DashboardSessionItem[];
} 
 /** Dashboard del profesional: nuevas entrevistas y uúúúltimas sesiones. */
@Component({ 
 selector: 'app-dashboard-profesional',   standalone: true,   imports: [AsyncPipe, RouterLink, StatusBadgeComponent],   templateUrl: './dashboard-profesional.component.html',   styleUrl: './dashboard-profesional.component.scss',
})
export class DashboardProfesionalComponent { 
 private api = inject(ApiService); 
 data$: Observable<DashboardProfesionalData> = forkJoin({ 
 youths: this.api.getYouths(),   sessions: this.api.getSessionsWithTemplateLabel(),   }).pipe(   switchMap(({ youths, sessions }) => { 
 const youthMap = new Map<string, Youth>(youths.map((y) => [y.id, y])); 
 const ordered = [...sessions].sort((a, b) => this.sessionTimestamp(b) - this.sessionTimestamp(a)); 
 const recentCompleted = ordered.filter((s) => s.status === 'COMPLETADA').slice(0, 8); 
 const summaries$ = recentCompleted.length ? forkJoin(recentCompleted.map((session) => this.api.getSessionSummary(session.id))) : of([]); 
 return summaries$.pipe(   map((summaries) => { 
 const pendingSessions = recentCompleted   .filter((session, index) => !summaries[index])   .map((s) => ({ ...this.buildSessionItem(s, youthMap), pendingFeedback: true })); 
 const pendingIds = new Set(pendingSessions.map((s) => s.id)); 
 const inProgressSessions = ordered   .filter((s) => s.status === 'EN_CURSO')   .slice(0, 6)   .map((s) => this.buildSessionItem(s, youthMap)); 
 const completedSessions = ordered   .filter((s) => s.status === 'COMPLETADA')   .filter((s) => !pendingIds.has(s.id))   .slice(0, 8)   .map((s) => this.buildSessionItem(s, youthMap)); 
 return { 
 pendingSessions,   inProgressSessions,   completedSessions,   }; 
 })   ); 
 })   ); 
 private buildSessionItem(session: SessionWithTemplateLabel, youthMap: Map<string, Youth>): DashboardSessionItem { 
 const youth = youthMap.get(session.youth_id); 
 return { 
 id: session.id,   youthId: session.youth_id,   youthName: youth?.display_name ?? 'Joven',   youthRut: youth?.rut,   youthPhotoUrl: youth?.profile_photo_url,   status: session.status,   mode: session.mode,   started_at: session.started_at,   templateLabel: session.templateLabel,   }; 
 } 
 private sessionTimestamp(session: Session): number { 
 const iso = session.ended_at || session.started_at; 
 if (!iso) return 0; 
 const ts = new Date(iso).getTime(); 
 return Number.isNaN(ts) ? 0 : ts; 
 } 
 initials(name?: string | null): string { 
 if (!name) return 'J'; 
 const parts = name.trim().split(/\s+/).filter(Boolean); 
 if (parts.length === 0) return 'J'; 
 if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase(); 
 return (parts[0][0] + parts[1][0]).toUpperCase(); 
 } 
 readonly formatDate = formatDate; 
 modeLabel(mode: Session['mode']): string { 
 return mode === 'AUTOGESTIONADA' ? 'Autogestionada' : 'Supervisada'; 
 }
}
