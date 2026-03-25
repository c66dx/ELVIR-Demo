import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';
import { ApiService } from '../../../core/services/api.service';
import type { YouthWithLastSession } from '../../../core/services/api.service';
import type { Session } from '../../../core/models/session.model';
import { formatDate, formatStatusLabel } from '../../../shared/utils/date-format.util'; 
 type YouthRow = YouthWithLastSession & { 
 performanceLabel: string; 
 performanceNote?: string; 
 progressLabel: string; 
 progressTrend: 'up' | 'down' | 'flat' | 'none'; 
 interviewsLastMonth: number; 
 pendingFeedback: boolean; 
 pendingFeedbackCount: number; 
 pendingSessionId?: string;
}; 
/** Lista de jóvenes asignados al profesional. Filtros por búsqueda y login. */
@Component({ 
 selector: 'app-jovenes-list',   standalone: true,   imports: [FormsModule, RouterLink],   templateUrl: './jovenes-list.component.html',   styleUrl: './jovenes-list.component.scss',
})
export class JovenesListComponent implements OnInit { 
 private api = inject(ApiService); 
 youths: YouthRow[] = []; 
 loading = true; 
 page = 1; 
 total = 0; 
 readonly pageSize = 20; 
 filterSearch = ''; 
 filterLogin: '' | 'yes' | 'no' = ''; 
 private searchDebounce: ReturnType<typeof setTimeout> | null = null; 
 ngOnInit(): void { 
 this.loadYouths(); 
 } 
 loadYouths(): void { 
 this.loading = true; 
 const params: { search?: string; login_enabled?: boolean } = {}; 
 if (this.filterSearch.trim()) params.search = this.filterSearch.trim(); 
 if (this.filterLogin === 'yes') params.login_enabled = true; 
 if (this.filterLogin === 'no') params.login_enabled = false; 
 this.api   .getYouthsPaged({ ...params, page: this.page, page_size: this.pageSize })   .pipe(   switchMap((paged) => { 
 if (paged.items.length === 0) { 
 return of({ paged, rows: [] as YouthRow[] }); 
 } 
 return this.api.getSessions().pipe(   switchMap((sessions) => { 
 const youthIds = new Set(paged.items.map((y) => y.id)); 
 const sessionsForPage = sessions.filter((s) => youthIds.has(s.youth_id)); 
 const sessionsByYouth = this.groupSessionsByYouth(sessionsForPage); 
 const summaryTargets = sessionsForPage.filter((s) => s.status === 'COMPLETADA'); 
 const summaries$ = summaryTargets.length ? forkJoin(summaryTargets.map((session) => this.api.getSessionSummary(session.id))) : of([]); 
 return summaries$.pipe(   map((summaries) => { 
 const summaryMap = new Map<string, boolean>(); 
 summaries.forEach((summary, index) => { 
 if (summary) summaryMap.set(summaryTargets[index].id, true); 
 }); 
 return { 
 paged,   rows: this.buildRows(paged.items, sessionsByYouth, summaryMap),   }; 
 })   ); 
 })   ); 
 })   )   .subscribe({ 
 next: ({ paged, rows }) => { 
 this.youths = rows; 
 this.total = paged.total; 
 this.page = paged.page; 
 this.loading = false; 
 },   error: () => (this.loading = false),   }); 
 } 
 onFilterChange(): void { 
 this.page = 1; 
 this.loadYouths(); 
 } 
 onSearchInput(): void { 
 if (this.searchDebounce) clearTimeout(this.searchDebounce); 
 this.searchDebounce = setTimeout(() => { 
 this.page = 1; 
 this.loadYouths(); 
 }, 350); 
 } 
 clearFilters(): void { 
 this.filterSearch = ''; 
 this.filterLogin = ''; 
 this.page = 1; 
 this.loadYouths(); 
 } 
 readonly formatDate = formatDate; 
 readonly formatStatusLabel = formatStatusLabel; 
 totalPages(): number { 
 return Math.max(1, Math.ceil(this.total / this.pageSize)); 
 } 
 prevPage(): void { 
 if (this.page > 1) { 
 this.page -= 1; 
 this.loadYouths(); 
 } 
 } 
 nextPage(): void { 
 if (this.page < this.totalPages()) { 
 this.page += 1; 
 this.loadYouths(); 
 } 
 } 
 onDeactivate(youth: YouthWithLastSession): void { 
 if (!confirm(`Desactivar a ${youth.display_name}?`)) return; 
 this.api.deactivateYouth(youth.id).subscribe({ 
 next: () => this.loadYouths(),   }); 
 } 
 onActivate(youth: YouthWithLastSession): void { 
 if (!confirm(`Reactivar a ${youth.display_name}?`)) return; 
 this.api.activateYouth(youth.id).subscribe({ 
 next: () => this.loadYouths(),   }); 
 } 
 initials(name?: string | null): string { 
 if (!name) return 'J'; 
 const parts = name.trim().split(/\s+/).filter(Boolean); 
 if (parts.length === 0) return 'J'; 
 if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase(); 
 return (parts[0][0] + parts[1][0]).toUpperCase(); 
 } 
 private groupSessionsByYouth(sessions: Session[]): Map<string, Session[]> { 
 const map = new Map<string, Session[]>(); 
 sessions.forEach((session) => { 
 const list = map.get(session.youth_id)  ?? []; 
 list.push(session); 
 map.set(session.youth_id, list); 
 }); 
 return map; 
 } 
 private latestCompletedByYouth(sessionsByYouth: Map<string, Session[]>): Map<string, Session> { 
 const map = new Map<string, Session>(); 
 sessionsByYouth.forEach((sessions, youthId) => { 
 const latest = this.pickLatestCompleted(sessions); 
 if (latest) map.set(youthId, latest); 
 }); 
 return map; 
 } 
 private buildRows(   youths: YouthWithLastSession[],   sessionsByYouth: Map<string, Session[]>,   summaryMap: Map<string, boolean>   ): YouthRow[] { 
 const now = Date.now(); 
 const monthMs = 1000 * 60 * 60 * 24 * 30; 
 const lastMonthStart = now - monthMs; 
 const prevMonthStart = now - monthMs * 2; 
 return youths.map((youth) => { 
 const sessions = sessionsByYouth.get(youth.id)  ?? []; 
 const completed = sessions.filter((s) => s.status === 'COMPLETADA'); 
 const latestCompleted = this.pickLatest(completed); 
 const lastMonthCount = completed.filter((s) => this.isBetween(s, lastMonthStart, now)).length; 
 const prevMonthCount = completed.filter((s) => this.isBetween(s, prevMonthStart, lastMonthStart)).length; 
 const progress = this.buildProgress(lastMonthCount, prevMonthCount); 
 const performance = this.buildPerformance(latestCompleted, completed, sessions); 
 const pendingSessions = completed   .filter((s) => !summaryMap.has(s.id))   .sort((a, b) => this.sessionTimestamp(b) - this.sessionTimestamp(a)); 
 const pendingFeedbackCount = pendingSessions.length; 
 const pendingFeedback = pendingFeedbackCount > 0; 
 const pendingSessionId = pendingFeedbackCount === 1 ?  pendingSessions[0]?.id : undefined; 
 return { 
 ...youth,   performanceLabel: performance.label,   performanceNote: performance.note,   progressLabel: progress.label,   progressTrend: progress.trend,   interviewsLastMonth: lastMonthCount,   pendingFeedback,   pendingFeedbackCount,   pendingSessionId,   }; 
 }); 
 } 
 private buildPerformance(   latestCompleted: Session | null,   completed: Session[],   allSessions: Session[]   ): { label: string; note?: string } { 
 if (latestCompleted) { 
 const score = this.extractScoreFromMetrics(latestCompleted.metrics); 
 if (score != null) { 
 return { label: `${Math.round(score)}%`, note: 'IA' }; 
 } 
 } 
 if (allSessions.length > 0) { 
 const completionRate = Math.round((completed.length / Math.max(1, allSessions.length)) * 100); 
 return { label: `${completionRate}%`, note: 'Estimado' }; 
 } 
 return { label: 'Sin datos', note: 'Sin entrevistas' }; 
 } 
 private buildProgress(current: number, previous: number): { label: string; trend: 'up' | 'down' | 'flat' | 'none' } { 
 if (current === 0 && previous === 0) { 
 return { label: 'Sin actividad', trend: 'none' }; 
 } 
 if (previous === 0) { 
 return { label: '+100% (Nuevo)', trend: 'up' }; 
 } 
 const change = Math.round(((current - previous) / previous) * 100); 
 if (change === 0) { 
 return { label: '0% (Estancado)', trend: 'flat' }; 
 } 
 if (change > 0) { 
 return { label: `+${change}%`, trend: 'up' }; 
 } 
 return { label: `${change}%`, trend: 'down' }; 
 } 
 private pickLatestCompleted(sessions: Session[]): Session | null { 
 return this.pickLatest(sessions.filter((s) => s.status === 'COMPLETADA')); 
 } 
 private pickLatest(sessions: Session[]): Session | null { 
 if (sessions.length === 0) return null; 
 return sessions.reduce((latest, session) =>   this.sessionTimestamp(session) > this.sessionTimestamp(latest) ? session : latest   ); 
 } 
 private isBetween(session: Session, start: number, end: number): boolean { 
 const ts = this.sessionTimestamp(session); 
 if (!ts) return false; 
 return ts >= start && ts < end; 
 } 
 private sessionTimestamp(session: Session): number { 
 const iso = session.ended_at || session.started_at; 
 if (!iso) return 0; 
 const ts = new Date(iso).getTime(); 
 return Number.isNaN(ts) ? 0 : ts; 
 } 
 private extractScoreFromMetrics(metrics?: Record<string, unknown>): number | null { 
 const evalData = metrics?.['prompt_evaluation']; 
 if (!evalData || typeof evalData !== 'object' || Array.isArray(evalData)) return null; 
 const directKeys = [   'overall_score',   'overallScore',   'score',   'puntaje',   'rating',   'desempeno',   'performance',   'promedio',   'average',   'avg',   ]; 
 for (const key of directKeys) { 
 const value = this.parseNumeric((evalData as Record<string, unknown>)[key]); 
 if (value != null) return this.normalizeScore(value); 
 } 
 const overall = (evalData as Record<string, unknown>)['overall']; 
 if (overall && typeof overall === 'object' && !Array.isArray(overall)) { 
 for (const key of directKeys) { 
 const value = this.parseNumeric((overall as Record<string, unknown>)[key]); 
 if (value != null) return this.normalizeScore(value); 
 } 
 } 
 return null; 
 } 
 private parseNumeric(value: unknown): number | null { 
 if (typeof value === 'number' && Number.isFinite(value)) return value; 
 if (typeof value === 'string') { 
 const parsed = Number(value); 
 if (!Number.isNaN(parsed)) return parsed; 
 } 
 return null; 
 } 
 private normalizeScore(raw: number): number { 
 if (!Number.isFinite(raw)) return 0; 
 if (raw <= 1) return raw * 100; 
 if (raw <= 5) return raw * 20; 
 if (raw <= 10) return raw * 10; 
 if (raw > 100) return 100; 
 return raw; 
 }
}
