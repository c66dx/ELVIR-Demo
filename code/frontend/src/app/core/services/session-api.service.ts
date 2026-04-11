import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of, forkJoin, throwError } from 'rxjs';
import { map, catchError, switchMap } from 'rxjs/operators';
import type { SessionStatus, SessionMode } from '@core/models/types.model';
import type { Session } from '@core/models/session.model';
import type { InterviewSummary } from '@core/models/interview-summary.model';
import type { TranscriptResponse } from '@core/models/transcript.model';
import type { SessionEvent } from '@core/models/session-event.model';
import type { SessionAudio } from '@core/models/session-audio.model';
import { API_BASE, str, withRequestId } from '@core/services/api-http-helpers';
import { CatalogApiService } from '@core/services/catalog-api.service';
import type { SessionWithTemplateLabel, PagedResult, PlatformSessionItem } from '@core/services/api-types';

/**
 * Sesiones de entrevista, contexto, plataforma (login/logout joven), transcripción, resúmenes y competencias por sesión.
 * Catalogos cargo/caso/plantilla: CatalogApiService. Uso directo en pantallas (inyectar SessionApiService).
 */
@Injectable({ providedIn: 'root' })
export class SessionApiService {
  private http = inject(HttpClient);
  private catalog = inject(CatalogApiService);

  getSessionContext(sessionId: string): Observable<{ jobRoleName: string; caseName: string } | null> {
    return this.http
      .get<{ jobRoleName: string; caseName: string }>(`${API_BASE}/sessions/${sessionId}/context`)
      .pipe(catchError(() => of(null)));
  }

  /** Lista entradas/salidas del joven a la plataforma (login/logout). Solo si tiene user_id. */
  getPlatformSessions(youthId: string): Observable<PlatformSessionItem[]> {
    return this.http.get<unknown[]>(`${API_BASE}/youths/${youthId}/platform-sessions`).pipe(
      map((list) =>
        ((list || []) as Record<string, unknown>[]).map((s) => ({
          id: str(s.id),
          user_id: str(s.user_id),
          started_at: s.started_at as string,
          ended_at: s.ended_at as string | undefined,
        }))
      ),
      catchError(() => of([]))
    );
  }

  getPlatformSessionsPaged(
    youthId: string,
    params?: { page?: number; page_size?: number }
  ): Observable<PagedResult<PlatformSessionItem>> {
    let httpParams = new HttpParams();
    if (params?.page) httpParams = httpParams.set('page', String(params.page));
    if (params?.page_size) httpParams = httpParams.set('page_size', String(params.page_size));
    return this.http
      .get<unknown[]>(`${API_BASE}/youths/${youthId}/platform-sessions`, { params: httpParams, observe: 'response' })
      .pipe(
        map((res) => {
          const list = (res.body || []) as Record<string, unknown>[];
          const total = Number(res.headers.get('X-Total-Count')) || list.length;
          const page = Number(res.headers.get('X-Page')) || params?.page || 1;
          const pageSize = Number(res.headers.get('X-Page-Size')) || params?.page_size || list.length;
          const items = list.map((s) => ({
            id: str(s.id),
            user_id: str(s.user_id),
            started_at: s.started_at as string,
            ended_at: s.ended_at as string | undefined,
          }));
          return { items, total, page, page_size: pageSize };
        }),
        catchError(() => of({ items: [], total: 0, page: params?.page || 1, page_size: params?.page_size || 0 }))
      );
  }

  createSession(data: {
    youth_id: string;
    simulation_template_id: string;
    mode: SessionMode;
    professional_id?: string;
  }): Observable<Session> {
    const body = {
      youth_id: Number(data.youth_id),
      simulation_template_id: Number(data.simulation_template_id),
      mode: data.mode,
      professional_id: data.professional_id ? Number(data.professional_id) : undefined,
    };
    return this.http.post<Record<string, unknown>>(`${API_BASE}/sessions`, body).pipe(
      map((s) => ({
        id: str(s.id),
        youth_id: str(s.youth_id),
        professional_id: s.professional_id != null ? str(s.professional_id) : undefined,
        simulation_template_id: str(s.simulation_template_id),
        mode: s.mode as SessionMode,
        status: s.status as SessionStatus,
        started_at: s.started_at as string,
        ended_at: s.ended_at as string | undefined,
        duration_seconds: s.duration_seconds as number | undefined,
        liveavatar_session_id: s.liveavatar_session_id as string | undefined,
        metrics: s.metrics as Record<string, unknown> | undefined,
        created_at: '',
        updated_at: '',
      }))
    );
  }

  getSessionEvents(sessionId: string): Observable<SessionEvent[]> {
    return this.http
      .get<unknown[]>(`${API_BASE}/sessions/${sessionId}/events`)
      .pipe(
        map((list) =>
          ((list || []) as Record<string, unknown>[]).map((e) => ({
            id: str(e.id),
            session_id: str(e.session_id),
            event_type: e.event_type as string,
            occurred_at: (e.occurred_at as string) ?? '',
            payload: e.payload as Record<string, unknown> | undefined,
          }))
        )
      );
  }

  getSessions(params?: { youth_id?: string }): Observable<Session[]> {
    let httpParams = new HttpParams();
    if (params?.youth_id) httpParams = httpParams.set('youth_id', params.youth_id);
    return this.http.get<unknown[]>(`${API_BASE}/sessions`, { params: httpParams }).pipe(
      map((list) =>
        ((list || []) as Record<string, unknown>[]).map((s) => ({
          id: str(s.id),
          youth_id: str(s.youth_id),
          professional_id: s.professional_id != null ? str(s.professional_id) : undefined,
          simulation_template_id: str(s.simulation_template_id),
          mode: s.mode as SessionMode,
          status: s.status as SessionStatus,
          started_at: s.started_at as string,
          ended_at: s.ended_at as string | undefined,
          duration_seconds: s.duration_seconds as number | undefined,
          liveavatar_session_id: s.liveavatar_session_id as string | undefined,
          metrics: s.metrics as Record<string, unknown> | undefined,
          created_at: '',
          updated_at: '',
        }))
      )
    );
  }

  getSessionsPaged(params?: {
    youth_id?: string;
    search?: string;
    status?: SessionStatus;
    mode?: SessionMode;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }): Observable<PagedResult<Session>> {
    let httpParams = new HttpParams();
    if (params?.youth_id) httpParams = httpParams.set('youth_id', params.youth_id);
    if (params?.search?.trim()) httpParams = httpParams.set('search', params.search.trim());
    if (params?.status) httpParams = httpParams.set('status', params.status);
    if (params?.mode) httpParams = httpParams.set('mode', params.mode);
    if (params?.start_date) httpParams = httpParams.set('start_date', params.start_date);
    if (params?.end_date) httpParams = httpParams.set('end_date', params.end_date);
    if (params?.page) httpParams = httpParams.set('page', String(params.page));
    if (params?.page_size) httpParams = httpParams.set('page_size', String(params.page_size));
    return this.http.get<unknown[]>(`${API_BASE}/sessions`, { params: httpParams, observe: 'response' }).pipe(
      map((res) => {
        const list = (res.body || []) as Record<string, unknown>[];
        const total = Number(res.headers.get('X-Total-Count')) || list.length;
        const page = Number(res.headers.get('X-Page')) || params?.page || 1;
        const pageSize = Number(res.headers.get('X-Page-Size')) || params?.page_size || list.length;
        const items = list.map((s) => ({
          id: str(s.id),
          youth_id: str(s.youth_id),
          professional_id: s.professional_id != null ? str(s.professional_id) : undefined,
          simulation_template_id: str(s.simulation_template_id),
          mode: s.mode as SessionMode,
          status: s.status as SessionStatus,
          started_at: s.started_at as string,
          ended_at: s.ended_at as string | undefined,
          duration_seconds: s.duration_seconds as number | undefined,
          liveavatar_session_id: s.liveavatar_session_id as string | undefined,
          metrics: s.metrics as Record<string, unknown> | undefined,
          created_at: '',
          updated_at: '',
        }));
        return { items, total, page, page_size: pageSize };
      }),
      catchError(() => of({ items: [], total: 0, page: params?.page || 1, page_size: params?.page_size || 0 }))
    );
  }

  /** Sesiones con templateLabel (cargo / caso) para mostrar en historial y perfil. */
  getSessionsWithTemplateLabel(params?: { youth_id?: string }): Observable<SessionWithTemplateLabel[]> {
    return this.getSessions(params).pipe(
      switchMap((sessions) =>
        forkJoin({
          jobRoles: this.catalog.getJobRoles(),
          cases: this.catalog.getCases(),
          templates: this.catalog.getSimulationTemplates(),
        }).pipe(
          map(({ jobRoles, cases, templates }) => {
            const jobMap = new Map(jobRoles.map((j) => [j.id, j]));
            const caseMap = new Map(cases.map((c) => [c.id, c]));
            return sessions.map((s) => {
              const t = templates.find((tpl) => tpl.id === s.simulation_template_id);
              const jobName = t ? jobMap.get(t.job_role_id)?.name : '';
              const caseName = t ? caseMap.get(t.case_id)?.name : '';
              return {
                ...s,
                templateLabel: jobName && caseName ? `${jobName} / ${caseName}` : '-',
              };
            });
          })
        )
      )
    );
  }

  getSessionsWithTemplateLabelPaged(params?: {
    youth_id?: string;
    search?: string;
    status?: SessionStatus;
    mode?: SessionMode;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }): Observable<PagedResult<SessionWithTemplateLabel>> {
    return this.getSessionsPaged(params).pipe(
      switchMap((paged) =>
        forkJoin({
          jobRoles: this.catalog.getJobRoles(),
          cases: this.catalog.getCases(),
          templates: this.catalog.getSimulationTemplates(),
        }).pipe(
          map(({ jobRoles, cases, templates }) => {
            const jobMap = new Map(jobRoles.map((j) => [j.id, j]));
            const caseMap = new Map(cases.map((c) => [c.id, c]));
            const items = paged.items.map((s) => {
              const t = templates.find((tpl) => tpl.id === s.simulation_template_id);
              const jobName = t ? jobMap.get(t.job_role_id)?.name : '';
              const caseName = t ? caseMap.get(t.case_id)?.name : '';
              return {
                ...s,
                templateLabel: jobName && caseName ? `${jobName} / ${caseName}` : '-',
              };
            });
            return { ...paged, items };
          })
        )
      )
    );
  }

  getSessionStats(params?: { youth_id?: string; months?: number }): Observable<{
    total: number;
    completed: number;
    cancelled: number;
    error: number;
    in_progress: number;
    monthly: { month: string; count: number }[];
  }> {
    let httpParams = new HttpParams();
    if (params?.youth_id) httpParams = httpParams.set('youth_id', params.youth_id);
    if (params?.months) httpParams = httpParams.set('months', String(params.months));
    return this.http.get<Record<string, unknown>>(`${API_BASE}/sessions/stats`, { params: httpParams }).pipe(
      map((r) => ({
        total: Number(r.total) || 0,
        completed: Number(r.completed) || 0,
        cancelled: Number(r.cancelled) || 0,
        error: Number(r.error) || 0,
        in_progress: Number(r.in_progress) || 0,
        monthly: ((r.monthly as Record<string, unknown>[]) || []).map((m) => ({
          month: (m.month as string) ?? '',
          count: Number(m.count) || 0,
        })),
      })),
      catchError(() =>
        of({
          total: 0,
          completed: 0,
          cancelled: 0,
          error: 0,
          in_progress: 0,
          monthly: [],
        })
      )
    );
  }

  getSession(id: string): Observable<Session> {
    return this.http.get<Record<string, unknown>>(`${API_BASE}/sessions/${id}`).pipe(
      map((s) => ({
        id: str(s.id),
        youth_id: str(s.youth_id),
        professional_id: s.professional_id != null ? str(s.professional_id) : undefined,
        simulation_template_id: str(s.simulation_template_id),
        mode: s.mode as SessionMode,
        status: s.status as SessionStatus,
        started_at: s.started_at as string,
        ended_at: s.ended_at as string | undefined,
        duration_seconds: s.duration_seconds as number | undefined,
        liveavatar_session_id: s.liveavatar_session_id as string | undefined,
        metrics: s.metrics as Record<string, unknown> | undefined,
        created_at: '',
        updated_at: '',
      })),
      catchError((err) => throwError(() => err))
    );
  }

  /**
   * Inicia sesión en LiveAvatar. Si configurado: livekit_url + access_token.
   * Si no: embed iframe placeholder.
   */
  startSession(id: string): Observable<{
    session_id: string;
    liveavatar_session_id: string;
    livekit_url?: string;
    access_token?: string;
    embed?: { type: 'iframe'; url: string };
    /** Motivo cuando no hay LiveKit (error API, no configurado, etc.) */
    fallback_detail?: string;
  }> {
    return this.http
      .post<{
        session_id: number;
        liveavatar_session_id: string;
        livekit_url?: string;
        access_token?: string;
        embed?: { type: string; url: string };
        fallback_detail?: string | null;
      }>(`${API_BASE}/sessions/${id}/start`, {})
      .pipe(
        map((r) => ({
          session_id: str(r.session_id),
          liveavatar_session_id: r.liveavatar_session_id,
          livekit_url: r.livekit_url,
          access_token: r.access_token,
          embed: r.embed ? { type: 'iframe' as const, url: r.embed.url } : undefined,
          fallback_detail: r.fallback_detail ?? undefined,
        })),
        catchError((err) => throwError(() => err))
      );
  }

  /** Mantiene viva una sesión en curso actualizando last_heartbeat_at. */
  heartbeatSession(id: string): Observable<{ ok: boolean; status?: string } | null> {
    return this.http
      .post<{ ok: boolean; status?: string }>(`${API_BASE}/sessions/${id}/heartbeat`, {})
      .pipe(catchError(() => of(null)));
  }

  closeSession(
    id: string,
    data: { status: SessionStatus; metrics?: Record<string, unknown>; motivo?: string }
  ): Observable<Session | null> {
    const body: Record<string, unknown> = { status: data.status };
    if (data.metrics) body.metrics = data.metrics;
    if (data.motivo) body.motivo = data.motivo;
    return this.http
      .post<Record<string, unknown>>(`${API_BASE}/sessions/${id}/close`, body)
      .pipe(
        map((s) => ({
          id: str(s.id),
          youth_id: '',
          simulation_template_id: '',
          mode: 'AUTOGESTIONADA' as SessionMode,
          status: s.status as SessionStatus,
          started_at: '',
          ended_at: s.ended_at as string | undefined,
          duration_seconds: s.duration_seconds as number | undefined,
          created_at: '',
          updated_at: '',
        })),
        catchError(() => of(null))
      );
  }

  getSessionTranscript(sessionId: string): Observable<TranscriptResponse | null> {
    return this.http
      .get<TranscriptResponse | null>(`${API_BASE}/sessions/${sessionId}/transcript`)
      .pipe(
        map((t) => t ?? null),
        catchError(() => of(null))
      );
  }

  uploadSessionAudio(
    sessionId: string,
    file: File,
    durationSeconds?: number
  ): Observable<SessionAudio | { error: string }> {
    const form = new FormData();
    form.append('file', file);
    if (durationSeconds != null) {
      form.append('duration_seconds', String(durationSeconds));
    }
    return this.http.post<Record<string, unknown>>(`${API_BASE}/sessions/${sessionId}/audio`, form).pipe(
      map((a) => ({
        id: str(a.id),
        session_id: str(a.session_id),
        url: a.url as string,
        content_type: a.content_type as string | undefined,
        file_size_bytes: a.file_size_bytes as number | undefined,
        duration_seconds: a.duration_seconds as number | undefined,
        created_at: (a.created_at as string) ?? '',
        updated_at: (a.updated_at as string) ?? '',
      })),
      catchError((err) => of({ error: withRequestId('Error al subir audio', err) }))
    );
  }

  getSessionAudio(sessionId: string): Observable<SessionAudio | null> {
    return this.http.get<Record<string, unknown>>(`${API_BASE}/sessions/${sessionId}/audio`).pipe(
      map((a) =>
        a
          ? {
              id: str(a.id),
              session_id: str(a.session_id),
              url: a.url as string,
              content_type: a.content_type as string | undefined,
              file_size_bytes: a.file_size_bytes as number | undefined,
              duration_seconds: a.duration_seconds as number | undefined,
              created_at: (a.created_at as string) ?? '',
              updated_at: (a.updated_at as string) ?? '',
            }
          : null
      ),
      catchError(() => of(null))
    );
  }

  getSessionSummary(sessionId: string): Observable<InterviewSummary | null> {
    return this.http
      .get<Record<string, unknown>>(`${API_BASE}/sessions/${sessionId}/summary`)
      .pipe(
        map((s) =>
          s
            ? {
                id: str(s.id),
                session_id: str(s.session_id),
                professional_id: str(s.professional_id),
                summary_text: s.summary_text as string,
                competency_tags: s.competency_tags as string[] | undefined,
                created_at: (s.created_at as string) || '',
                updated_at: (s.updated_at as string) || '',
              }
            : null
        ),
        catchError(() => of(null))
      );
  }

  getSummariesByYouth(youthId: string): Observable<InterviewSummary[]> {
    return this.getSessions({ youth_id: youthId }).pipe(
      switchMap((sessions) => {
        const ids = sessions.map((s) => s.id).filter(Boolean);
        if (ids.length === 0) return of([]);
        return forkJoin(ids.map((sid) => this.getSessionSummary(sid))).pipe(
          map((summaries) => summaries.filter((s): s is InterviewSummary => s != null))
        );
      }),
      catchError(() => of([]))
    );
  }

  createSessionSummary(
    sessionId: string,
    data: { summary_text: string; competency_tags?: string[] }
  ): Observable<InterviewSummary | null> {
    return this.http
      .post<Record<string, unknown>>(`${API_BASE}/sessions/${sessionId}/summary`, data)
      .pipe(
        map((s) =>
          s
            ? {
                id: str(s.id),
                session_id: str(s.session_id),
                professional_id: str(s.professional_id),
                summary_text: s.summary_text as string,
                competency_tags: s.competency_tags as string[] | undefined,
                created_at: (s.created_at as string) || '',
                updated_at: (s.updated_at as string) || '',
              }
            : null
        ),
        catchError(() => of(null))
      );
  }

  /** Catálogo de competencias. */
  getCompetencies(): Observable<{ id: string; slug: string; name: string; is_active: boolean }[]> {
    return this.http.get<unknown[]>(`${API_BASE}/competencies`).pipe(
      map((list) =>
        ((list || []) as Record<string, unknown>[]).map((c) => ({
          id: str(c.id),
          slug: c.slug as string,
          name: c.name as string,
          is_active: (c.is_active as boolean) ?? true,
        }))
      )
    );
  }

  /** Niveles de competencia (BAJO, MEDIO, ALTO). */
  getCompetencyLevels(): Observable<{ id: string; slug: string; label: string; sort_order: number }[]> {
    return this.http.get<unknown[]>(`${API_BASE}/competency-levels`).pipe(
      map((list) =>
        ((list || []) as Record<string, unknown>[]).map((l) => ({
          id: str(l.id),
          slug: l.slug as string,
          label: l.label as string,
          sort_order: (l.sort_order as number) ?? 0,
        }))
      )
    );
  }

  /** Obtiene evaluación por competencias de una sesión. */
  getSessionCompetencies(sessionId: string): Observable<{
    session_id: number;
    items: { competency: { slug: string; name: string }; level: { slug: string; label: string }; comment: string | null }[];
  }> {
    return this.http.get<{
      session_id: number;
      items: { competency: { slug: string; name: string }; level: { slug: string; label: string }; comment: string | null }[];
    }>(`${API_BASE}/sessions/${sessionId}/competencies`);
  }

  /** Registra evaluación por competencias de una sesión. */
  createSessionCompetencies(
    sessionId: string,
    items: { competency_slug: string; level_slug: string; comment?: string }[]
  ): Observable<{ session_id: number; items_count: number }> {
    return this.http.post<{ session_id: number; items_count: number }>(
      `${API_BASE}/sessions/${sessionId}/competencies`,
      { items }
    );
  }
}
