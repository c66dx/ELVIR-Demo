import { Injectable, inject } from '@angular/core';
import { forkJoin, of, Observable } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';
import type { Session } from '@core/models/session.model';
import type { YouthWithLastSession, PagedResult } from '@core/services/api-types';
import { SessionApiService } from '@core/services/session-api.service';
import { YouthApiService } from '@core/services/youth-api.service';

export type YouthRow = YouthWithLastSession & {
  performanceLabel: string;
  performanceNote?: string;
  progressLabel: string;
  progressTrend: 'up' | 'down' | 'flat' | 'none';
  interviewsLastMonth: number;
  pendingFeedback: boolean;
  pendingFeedbackCount: number;
  pendingSessionId?: string;
};

export interface YouthListFilters {
  page: number;
  pageSize: number;
  search?: string;
  loginEnabled?: boolean;
}

@Injectable({ providedIn: 'root' })
export class YouthsFacade {
  private youths = inject(YouthApiService);
  private sessions = inject(SessionApiService);

  getYouthsPage(filters: YouthListFilters): Observable<PagedResult<YouthRow>> {
    const params: { search?: string; login_enabled?: boolean; page?: number; page_size?: number } = {
      page: filters.page,
      page_size: filters.pageSize,
    };
    if (filters.search?.trim()) params.search = filters.search.trim();
    if (filters.loginEnabled !== undefined) params.login_enabled = filters.loginEnabled;

    return this.youths.getYouthsPaged(params).pipe(
      switchMap((paged) => {
        if (paged.items.length === 0) {
          return of({ ...paged, items: [] as YouthRow[] });
        }
        return this.sessions.getSessions().pipe(
          switchMap((sessions) => {
            const youthIds = new Set(paged.items.map((y) => y.id));
            const sessionsForPage = sessions.filter((s) => youthIds.has(s.youth_id));
            const sessionsByYouth = this.groupSessionsByYouth(sessionsForPage);
            const summaryTargets = sessionsForPage.filter((s) => s.status === 'COMPLETADA');
            const summaries$ = summaryTargets.length
              ? forkJoin(summaryTargets.map((session) => this.sessions.getSessionSummary(session.id)))
              : of([]);
            return summaries$.pipe(
              map((summaries) => {
                const summaryMap = new Map<string, boolean>();
                summaries.forEach((summary, index) => {
                  if (summary) summaryMap.set(summaryTargets[index].id, true);
                });
                const items = this.buildRows(paged.items, sessionsByYouth, summaryMap);
                return { ...paged, items };
              })
            );
          })
        );
      })
    );
  }

  deactivateYouth(youthId: string): Observable<void> {
    return this.youths.deactivateYouth(youthId);
  }

  activateYouth(youthId: string): Observable<void> {
    return this.youths.activateYouth(youthId);
  }

  private groupSessionsByYouth(sessions: Session[]): Map<string, Session[]> {
    const map = new Map<string, Session[]>();
    sessions.forEach((session) => {
      const list = map.get(session.youth_id) ?? [];
      list.push(session);
      map.set(session.youth_id, list);
    });
    return map;
  }

  private buildRows(
    youths: YouthWithLastSession[],
    sessionsByYouth: Map<string, Session[]>,
    summaryMap: Map<string, boolean>
  ): YouthRow[] {
    const now = Date.now();
    const monthMs = 1000 * 60 * 60 * 24 * 30;
    const lastMonthStart = now - monthMs;
    const prevMonthStart = now - monthMs * 2;
    return youths.map((youth) => {
      const sessions = sessionsByYouth.get(youth.id) ?? [];
      const completed = sessions.filter((s) => s.status === 'COMPLETADA');
      const latestCompleted = this.pickLatest(completed);
      const lastMonthCount = completed.filter((s) => this.isBetween(s, lastMonthStart, now)).length;
      const prevMonthCount = completed.filter((s) => this.isBetween(s, prevMonthStart, lastMonthStart)).length;
      const progress = this.buildProgress(lastMonthCount, prevMonthCount);
      const performance = this.buildPerformance(latestCompleted, completed, sessions);
      const pendingSessions = completed
        .filter((s) => !summaryMap.has(s.id))
        .sort((a, b) => this.sessionTimestamp(b) - this.sessionTimestamp(a));
      const pendingFeedbackCount = pendingSessions.length;
      const pendingFeedback = pendingFeedbackCount > 0;
      const pendingSessionId = pendingFeedbackCount === 1 ? pendingSessions[0]?.id : undefined;
      return {
        ...youth,
        performanceLabel: performance.label,
        performanceNote: performance.note,
        progressLabel: progress.label,
        progressTrend: progress.trend,
        interviewsLastMonth: lastMonthCount,
        pendingFeedback,
        pendingFeedbackCount,
        pendingSessionId,
      };
    });
  }

  private buildPerformance(
    latestCompleted: Session | null,
    completed: Session[],
    allSessions: Session[]
  ): { label: string; note?: string } {
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

  private pickLatest(sessions: Session[]): Session | null {
    if (sessions.length === 0) return null;
    return sessions.reduce((latest, session) =>
      this.sessionTimestamp(session) > this.sessionTimestamp(latest) ? session : latest
    );
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
    const directKeys = [
      'overall_score',
      'overallScore',
      'score',
      'puntaje',
      'rating',
      'desempeno',
      'performance',
      'promedio',
      'average',
      'avg',
    ];
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
