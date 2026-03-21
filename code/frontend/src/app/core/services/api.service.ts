import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of, forkJoin } from 'rxjs';
import { map, catchError, switchMap } from 'rxjs/operators';
import type { Role, SessionStatus, SessionMode, MaterialType, Difficulty } from '../models/types.model';
import type { Youth } from '../models/youth.model';
import type { Session } from '../models/session.model';
import type { JobRole } from '../models/job-role.model';
import type { Case } from '../models/case.model';
import type { SimulationTemplate } from '../models/simulation-template.model';
import type { SupportMaterial } from '../models/support-material.model';
import type { MaterialSuggestion } from '../models/material-suggestion.model';
import type { MaterialView } from '../models/material-view.model';
import type { InterviewSummary } from '../models/interview-summary.model';
import type { TranscriptResponse } from '../models/transcript.model';
import type { SessionEvent } from '../models/session-event.model';
import type { SessionAudio } from '../models/session-audio.model';
import { environment } from '../../../environments/environment';

/** Respuesta al crear joven: incluye activation_url si login_enabled. */
export type CreateYouthResponse = Youth & { activation_url?: string };

/** Respuesta al editar joven: incluye activation_url si se habilita login y no tiene user_id. */
export type UpdateYouthResponse = Youth & { activation_url?: string };

export interface YouthWithLastSession extends Youth {
  status_label?: string;
  last_session?: Pick<Session, 'id' | 'status' | 'started_at' | 'ended_at'>;
}

export interface SessionWithTemplateLabel extends Session {
  templateLabel?: string;
}

export interface PlatformSessionItem {
  id: string;
  user_id: string;
  started_at: string;
  ended_at?: string;
}

export interface AdminAssignedProfessional {
  id: string;
  display_name: string;
  email?: string;
  is_active: boolean;
}

export interface AdminYouthLogRow {
  id: string;
  user_id?: string;
  display_name: string;
  identifier?: string;
  rut?: string;
  email?: string;
  profile_photo_url?: string;
  login_enabled: boolean;
  is_active: boolean;
  login_type: string;
  last_login_at?: string;
  last_interview_at?: string;
  last_interview_status?: string;
  last_interview_mode?: string;
  assigned_professional?: AdminAssignedProfessional;
}

export interface AdminProfessionalLogRow {
  id: string;
  user_id: string;
  display_name: string;
  email?: string;
  is_active: boolean;
  login_type: string;
  last_login_at?: string;
}

export interface AdminListMeta {
  total: number;
  page: number;
  page_size: number;
}

export interface AdminUsersOverviewMeta {
  youths?: AdminListMeta;
  professionals?: AdminListMeta;
}

export interface AdminUsersOverview {
  youths: AdminYouthLogRow[];
  professionals: AdminProfessionalLogRow[];
  meta?: AdminUsersOverviewMeta;
}

export interface AdminPlatformLogItem {
  started_at: string;
  ended_at?: string;
}

export interface AdminInterviewLogItem {
  id: string;
  started_at: string;
  ended_at?: string;
  status: SessionStatus;
  mode: SessionMode;
  professional_id?: string;
  professional_name?: string;
}

export interface AdminYouthLogs {
  platform_sessions: AdminPlatformLogItem[];
  interviews: AdminInterviewLogItem[];
  meta?: {
    platform?: AdminListMeta;
    interviews?: AdminListMeta;
  };
}

export interface AuditLogRow {
  id: string;
  request_id?: string;
  actor_user_id?: string;
  actor_role?: string;
  actor_email?: string;
  action: string;
  entity_type?: string;
  entity_id?: string;
  status_code: number;
  method: string;
  path: string;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

export interface PagedResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export type YouthNotificationType = 'material' | 'feedback' | 'session' | 'general';

export interface YouthNotificationDto {
  id: string;
  youth_id: string;
  type: YouthNotificationType;
  title: string;
  message: string;
  link?: string;
  entity_type?: string;
  entity_id?: string;
  created_at: string;
  read_at?: string | null;
}

export interface YouthNotificationsPage extends PagedResult<YouthNotificationDto> {
  unread: number;
}

const API_BASE = environment.apiUrl;

/** Convierte IDs numéricos a string para compatibilidad con el frontend. */
function str(id: unknown): string {
  return id != null ? String(id) : '';
}

function withRequestId(message: string, err: unknown): string {
  const requestId = (err as { headers?: { get?: (name: string) => string | null } })?.headers?.get?.('X-Request-ID');
  return requestId ? `${message} (Código: ${requestId})` : message;
}

/** Servicio HTTP para la API REST de ELVIR. Métodos para auth, jóvenes, sesiones, catálogos, material. */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);

  /** El AuthInterceptor añade el token Bearer automáticamente a las peticiones autenticadas. */
  login(email: string, password: string): Observable<{ access_token: string; role: Role; user_id: string } | { error: string }> {
    return this.http
      .post<{ access_token: string; role: string; user_id: number }>(`${API_BASE}/auth/login`, { email, password })
      .pipe(
        map((r) => ({ access_token: r.access_token, role: r.role as Role, user_id: str(r.user_id) })),
        catchError((err) => {
          const d = err.error?.detail;
          const msg = typeof d === 'string' ? d : Array.isArray(d) ? d[0]?.msg ?? 'Credenciales inválidas' : 'Credenciales inválidas';
          return of({ error: withRequestId(msg, err) });
        })
      );
  }

  /** Registra cierre de sesión en backend (para métricas de plataforma). */
  logout(): Observable<void> {
    return this.http.post<void>(`${API_BASE}/auth/logout`, {}).pipe(
      catchError(() => of(undefined))
    );
  }

  getMe(): Observable<{ user_id: string; role: Role; email: string; profile_photo_url?: string; professional_id?: string; youth_id?: string } | null> {
    return this.http
      .get<{ user_id: number; role: string; email: string; profile_photo_url?: string; professional_id?: number; youth_id?: number }>(`${API_BASE}/auth/me`)
      .pipe(
        map((r) => ({
          user_id: str(r.user_id),
          role: r.role as Role,
          email: r.email,
          profile_photo_url: r.profile_photo_url ?? undefined,
          professional_id: r.professional_id != null ? str(r.professional_id) : undefined,
          youth_id: r.youth_id != null ? str(r.youth_id) : undefined,
        })),
        catchError(() => of(null))
      );
  }

  changePassword(current_password: string, new_password: string): Observable<{ success: true } | { error: string }> {
    return this.http
      .post<{ success: boolean; message?: string }>(`${API_BASE}/auth/change-password`, {
        current_password,
        new_password,
      })
      .pipe(
        map(() => ({ success: true as const })),
        catchError((err) => {
          const d = err.error?.detail;
          const msg = typeof d === 'string' ? d : 'Error al cambiar contraseña';
          return of({ error: withRequestId(msg, err) });
        })
      );
  }

  requestEmailChange(new_email: string, current_password: string): Observable<{ success: true; activation_url?: string } | { error: string }> {
    return this.http
      .post<{ success: boolean; activation_url?: string }>(`${API_BASE}/auth/change-email`, {
        new_email,
        current_password,
      })
      .pipe(
        map((r) => ({ success: true as const, activation_url: r.activation_url })),
        catchError((err) => {
          const d = err.error?.detail;
          const msg = typeof d === 'string' ? d : 'Error al solicitar cambio de email';
          return of({ error: withRequestId(msg, err) });
        })
      );
  }

  uploadProfilePhoto(file: File): Observable<{ url: string } | { error: string }> {
    const data = new FormData();
    data.append('file', file);
    return this.http.post<{ url: string }>(`${API_BASE}/auth/me/photo`, data).pipe(
      map((r) => ({ url: r.url })),
      catchError((err) => {
        const d = err.error?.detail;
        const msg = typeof d === 'string' ? d : 'Error al subir foto';
        return of({ error: withRequestId(msg, err) });
      })
    );
  }

  uploadYouthPhoto(youthId: string, file: File): Observable<Youth | { error: string }> {
    const data = new FormData();
    data.append('file', file);
    return this.http.post<Record<string, unknown>>(`${API_BASE}/youths/${youthId}/photo`, data).pipe(
      map((y) => ({
        id: str(y.id),
        user_id: y.user_id != null ? str(y.user_id) : undefined,
        display_name: y.display_name as string,
        identifier: y.identifier as string | undefined,
        rut: y.rut as string | undefined,
        email: y.email as string | undefined,
        profile_photo_url: y.profile_photo_url as string | undefined,
        phone: y.phone as string | undefined,
        year_of_birth: y.year_of_birth as number | undefined,
        diagnosis: y.diagnosis as string | undefined,
        login_enabled: (y.login_enabled as boolean) ?? false,
        is_active: (y.is_active as boolean) ?? true,
        general_notes: y.general_notes as string | undefined,
        profile_checklist: (y.profile_checklist as string[] | undefined) ?? undefined,
        created_at: '',
        updated_at: '',
      })),
      catchError((err) => {
        const d = err.error?.detail;
        const msg = typeof d === 'string' ? d : 'Error al subir foto';
        return of({ error: withRequestId(msg, err) });
      })
    );
  }

  getJobRoles(): Observable<JobRole[]> {
    return this.http.get<unknown[]>(`${API_BASE}/job-roles`).pipe(
      map((list) =>
        ((list || []) as Record<string, unknown>[]).map((r) => ({
          id: str(r.id),
          slug: r.slug as string,
          name: r.name as string,
          description: r.description as string | undefined,
          objetivo: r.objetivo as string | undefined,
          competencias: r.competencias as string | string[] | undefined,
          is_active: (r.is_active as boolean) ?? true,
        }))
      )
    );
  }

  getCases(): Observable<Case[]> {
    return this.http.get<unknown[]>(`${API_BASE}/cases`).pipe(
      map((list) =>
        ((list || []) as Record<string, unknown>[]).map((c) => ({
          id: str(c.id),
          slug: c.slug as string,
          name: c.name as string,
          difficulty: c.difficulty as Difficulty,
          prompt_instructions: c.prompt_instructions as string | undefined,
          is_active: (c.is_active as boolean) ?? true,
        }))
      )
    );
  }

  getSimulationTemplates(params?: { job_role_id?: string; case_id?: string }): Observable<SimulationTemplate[]> {
    let httpParams = new HttpParams();
    if (params?.job_role_id) httpParams = httpParams.set('job_role_id', params.job_role_id);
    if (params?.case_id) httpParams = httpParams.set('case_id', params.case_id);
    return this.http
      .get<unknown[]>(`${API_BASE}/simulation-templates`, { params: httpParams })
      .pipe(
        map((list) =>
          ((list || []) as Record<string, unknown>[]).map((t) => {
            const jr = t.job_role as Record<string, unknown> | undefined;
            const c = t.case as Record<string, unknown> | undefined;
            return {
              id: str(t.id),
              job_role_id: str(jr?.id),
              case_id: str(c?.id),
              liveavatar_context_id: t.liveavatar_context_id as string,
              liveavatar_avatar_id: t.liveavatar_avatar_id as string,
              liveavatar_voice_id: t.liveavatar_voice_id as string,
              is_active: (t.is_active as boolean) ?? true,
              created_at: '',
              updated_at: '',
            };
          })
        )
      );
  }

  getSimulationTemplateById(id: string): Observable<SimulationTemplate | null> {
    return this.http.get<Record<string, unknown>>(`${API_BASE}/simulation-templates/${id}`).pipe(
      map((t) => {
        if (!t) return null;
        const jr = t.job_role as Record<string, unknown> | undefined;
        const c = t.case as Record<string, unknown> | undefined;
        return {
          id: str(t.id),
          job_role_id: str(jr?.id),
          case_id: str(c?.id),
          liveavatar_context_id: t.liveavatar_context_id as string,
          liveavatar_avatar_id: t.liveavatar_avatar_id as string,
          liveavatar_voice_id: t.liveavatar_voice_id as string,
          is_active: (t.is_active as boolean) ?? true,
          created_at: '',
          updated_at: '',
        };
      }),
      catchError(() => of(null))
    );
  }

  getSessionContext(sessionId: string): Observable<{ jobRoleName: string; caseName: string } | null> {
    return this.http
      .get<{ jobRoleName: string; caseName: string }>(`${API_BASE}/sessions/${sessionId}/context`)
      .pipe(catchError(() => of(null)));
  }

  resolveSimulationTemplate(job_role_id: string): Observable<SimulationTemplate | null> {
    return this.http
      .get<Record<string, unknown>>(`${API_BASE}/simulation-templates/resolve`, {
        params: { job_role_id },
      })
      .pipe(
        map((t) => {
          if (!t) return null;
          const jr = t.job_role as Record<string, unknown> | undefined;
          const c = t.case as Record<string, unknown> | undefined;
          return {
            id: str(t.id),
            job_role_id: str(jr?.id),
            case_id: str(c?.id),
            liveavatar_context_id: t.liveavatar_context_id as string,
            liveavatar_avatar_id: t.liveavatar_avatar_id as string,
            liveavatar_voice_id: t.liveavatar_voice_id as string,
            is_active: (t.is_active as boolean) ?? true,
            created_at: '',
            updated_at: '',
          };
        }),
        catchError(() => of(null))
      );
  }

  getYouths(params?: { search?: string; is_active?: boolean; login_enabled?: boolean }): Observable<YouthWithLastSession[]> {
    let p = new HttpParams();
    if (params?.search?.trim()) p = p.set('search', params.search.trim());
    if (params?.is_active !== undefined) p = p.set('is_active', String(params.is_active));
    if (params?.login_enabled !== undefined) p = p.set('login_enabled', String(params.login_enabled));
    return this.http.get<unknown[]>(`${API_BASE}/youths`, { params: p }).pipe(
      map((list) =>
        ((list || []) as Record<string, unknown>[]).map((y) => {
          const ls = y.last_session as Record<string, unknown> | undefined;
          return {
            id: str(y.id),
            user_id: y.user_id != null ? str(y.user_id) : undefined,
            display_name: y.display_name as string,
            identifier: y.identifier as string | undefined,
            rut: y.rut as string | undefined,
            profile_photo_url: y.profile_photo_url as string | undefined,
            phone: y.phone as string | undefined,
            login_enabled: (y.login_enabled as boolean) ?? false,
            is_active: (y.is_active as boolean) ?? true,
            general_notes: y.general_notes as string | undefined,
            status_label: y.status_label as string | undefined,
            created_at: '',
            updated_at: '',
            last_session: ls
              ? {
                  id: str(ls.id),
                  status: ls.status as SessionStatus,
                  started_at: ls.started_at as string,
                  ended_at: ls.ended_at as string | undefined,
                }
              : undefined,
          };
        })
      )
    );
  }

  getYouthsPaged(params?: {
    search?: string;
    is_active?: boolean;
    login_enabled?: boolean;
    page?: number;
    page_size?: number;
  }): Observable<PagedResult<YouthWithLastSession>> {
    let p = new HttpParams();
    if (params?.search?.trim()) p = p.set('search', params.search.trim());
    if (params?.is_active !== undefined) p = p.set('is_active', String(params.is_active));
    if (params?.login_enabled !== undefined) p = p.set('login_enabled', String(params.login_enabled));
    if (params?.page) p = p.set('page', String(params.page));
    if (params?.page_size) p = p.set('page_size', String(params.page_size));
    return this.http.get<unknown[]>(`${API_BASE}/youths`, { params: p, observe: 'response' }).pipe(
      map((res) => {
        const list = (res.body || []) as Record<string, unknown>[];
        const total = Number(res.headers.get('X-Total-Count')) || list.length;
        const page = Number(res.headers.get('X-Page')) || params?.page || 1;
        const pageSize = Number(res.headers.get('X-Page-Size')) || params?.page_size || list.length;
          const items = list.map((y) => {
            const ls = y.last_session as Record<string, unknown> | undefined;
            return {
              id: str(y.id),
              user_id: y.user_id != null ? str(y.user_id) : undefined,
              display_name: y.display_name as string,
              identifier: y.identifier as string | undefined,
              rut: y.rut as string | undefined,
              profile_photo_url: y.profile_photo_url as string | undefined,
              phone: y.phone as string | undefined,
              login_enabled: (y.login_enabled as boolean) ?? false,
              is_active: (y.is_active as boolean) ?? true,
              general_notes: y.general_notes as string | undefined,
              status_label: y.status_label as string | undefined,
            created_at: '',
            updated_at: '',
            last_session: ls
              ? {
                  id: str(ls.id),
                  status: ls.status as SessionStatus,
                  started_at: ls.started_at as string,
                  ended_at: ls.ended_at as string | undefined,
                }
              : undefined,
          };
        });
        return { items, total, page, page_size: pageSize };
      }),
      catchError(() => of({ items: [], total: 0, page: params?.page || 1, page_size: params?.page_size || 0 }))
    );
  }

  getYouthLookup(ids: string[]): Observable<{ id: string; display_name: string; rut?: string; profile_photo_url?: string }[]> {
    const body = { ids: ids.map((id) => Number(id)).filter((id) => !Number.isNaN(id)) };
    return this.http.post<Record<string, unknown>[]>(`${API_BASE}/youths/lookup`, body).pipe(
      map((list) =>
        (list || []).map((y) => ({
          id: str(y.id),
          display_name: (y.display_name as string) ?? '',
          rut: y.rut as string | undefined,
          profile_photo_url: y.profile_photo_url as string | undefined,
        }))
      ),
      catchError(() => of([]))
    );
  }

  createYouth(data: Omit<Youth, 'id' | 'created_at' | 'updated_at'> & { email?: string }): Observable<CreateYouthResponse> {
    const body: Record<string, unknown> = {
      display_name: data.display_name,
      rut: data.rut,
      phone: data.phone,
      year_of_birth: data.year_of_birth,
      diagnosis: data.diagnosis,
      login_enabled: data.login_enabled,
      general_notes: data.general_notes,
      profile_checklist: data.profile_checklist,
    };
    if (data.email) body.email = data.email;
    return this.http.post<Record<string, unknown>>(`${API_BASE}/youths`, body).pipe(
      map((y) => ({
        id: str(y.id),
        user_id: y.user_id != null ? str(y.user_id) : undefined,
        display_name: y.display_name as string,
        identifier: y.identifier as string | undefined,
        rut: y.rut as string | undefined,
        phone: y.phone as string | undefined,
        login_enabled: (y.login_enabled as boolean) ?? false,
        is_active: (y.is_active as boolean) ?? true,
        general_notes: y.general_notes as string | undefined,
        profile_checklist: (y.profile_checklist as string[] | undefined) ?? undefined,
        created_at: '',
        updated_at: '',
        activation_url: y.activation_url as string | undefined,
      }))
    );
  }

  validateActivationToken(token: string): Observable<{ valid: boolean; email?: string; display_name?: string; error?: string; is_change_email?: boolean }> {
    return this.http
      .get<{ valid: boolean; email?: string; display_name?: string; error?: string; is_change_email?: boolean }>(
        `${API_BASE}/auth/activate/validate`,
        { params: { token } }
      )
      .pipe(catchError(() => of({ valid: false, error: 'TOKEN_NOT_FOUND' })));
  }

  activateAccount(params: {
    token: string;
    password?: string;
    current_password?: string;
  }): Observable<{ success: boolean; error?: string }> {
    const body: Record<string, string> = { token: params.token };
    if (params.password != null) body.password = params.password;
    if (params.current_password != null) body.current_password = params.current_password;
    return this.http.post<{ success: boolean; error?: string }>(`${API_BASE}/auth/activate`, body).pipe(
      map((r) => ({ success: r.success, error: r.error })),
      catchError((err) => of({ success: false, error: withRequestId(err.error?.error ?? 'TOKEN_NOT_FOUND', err) }))
    );
  }

  getYouth(id: string): Observable<Youth | null> {
    return this.http.get<Record<string, unknown>>(`${API_BASE}/youths/${id}`).pipe(
      map((y) => ({
        id: str(y.id),
        user_id: y.user_id != null ? str(y.user_id) : undefined,
        display_name: y.display_name as string,
        identifier: y.identifier as string | undefined,
        rut: y.rut as string | undefined,
        email: y.email as string | undefined,
        profile_photo_url: y.profile_photo_url as string | undefined,
        phone: y.phone as string | undefined,
        year_of_birth: y.year_of_birth as number | undefined,
        diagnosis: y.diagnosis as string | undefined,
        login_enabled: (y.login_enabled as boolean) ?? false,
        is_active: (y.is_active as boolean) ?? true,
        general_notes: y.general_notes as string | undefined,
        profile_checklist: (y.profile_checklist as string[] | undefined) ?? undefined,
        created_at: '',
        updated_at: '',
      })),
      catchError(() => of(null))
    );
  }

  updateYouth(id: string, data: Partial<Youth> & { email?: string }): Observable<UpdateYouthResponse | null> {
    const body: Record<string, unknown> = { ...data };
    delete body.identifier;
    return this.http.put<Record<string, unknown>>(`${API_BASE}/youths/${id}`, body).pipe(
      map((y) => ({
        id: str(y.id),
        user_id: y.user_id != null ? str(y.user_id) : undefined,
        display_name: y.display_name as string,
        identifier: y.identifier as string | undefined,
        rut: y.rut as string | undefined,
        phone: y.phone as string | undefined,
        year_of_birth: y.year_of_birth as number | undefined,
        diagnosis: y.diagnosis as string | undefined,
        login_enabled: (y.login_enabled as boolean) ?? false,
        is_active: (y.is_active as boolean) ?? true,
        general_notes: y.general_notes as string | undefined,
        profile_checklist: (y.profile_checklist as string[] | undefined) ?? undefined,
        created_at: '',
        updated_at: '',
        activation_url: y.activation_url as string | undefined,
      })),
      catchError(() => of(null))
    );
  }

  deactivateYouth(id: string): Observable<void> {
    return this.http.patch<void>(`${API_BASE}/youths/${id}/deactivate`, {});
  }

  activateYouth(id: string): Observable<void> {
    return this.http.patch<void>(`${API_BASE}/youths/${id}/activate`, {});
  }

  /** Cambia el email del joven y genera nuevo enlace de activación. */
  changeYouthEmail(youthId: string, newEmail: string): Observable<UpdateYouthResponse | null> {
    return this.http
      .post<Record<string, unknown>>(`${API_BASE}/youths/${youthId}/change-email`, { new_email: newEmail })
      .pipe(
        map((y) => ({
          id: str(y.id),
          user_id: y.user_id != null ? str(y.user_id) : undefined,
          display_name: y.display_name as string,
          identifier: y.identifier as string | undefined,
          rut: y.rut as string | undefined,
          email: y.email as string | undefined,
          phone: y.phone as string | undefined,
          year_of_birth: y.year_of_birth as number | undefined,
          diagnosis: y.diagnosis as string | undefined,
          login_enabled: (y.login_enabled as boolean) ?? false,
          is_active: (y.is_active as boolean) ?? true,
          general_notes: y.general_notes as string | undefined,
          profile_checklist: (y.profile_checklist as string[] | undefined) ?? undefined,
          created_at: '',
          updated_at: '',
          activation_url: y.activation_url as string | undefined,
        })),
        catchError(() => of(null))
      );
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

  /** Vista admin: resumen de usuarios con último login y última entrevista. */
  getAdminUsersOverview(params?: {
    tab?: 'youths' | 'professionals';
    page?: number;
    page_size?: number;
    search?: string;
  }): Observable<AdminUsersOverview> {
    let httpParams = new HttpParams();
    if (params?.tab) httpParams = httpParams.set('tab', params.tab);
    if (params?.page) httpParams = httpParams.set('page', String(params.page));
    if (params?.page_size) httpParams = httpParams.set('page_size', String(params.page_size));
    if (params?.search?.trim()) httpParams = httpParams.set('search', params.search.trim());
    return this.http.get<Record<string, unknown>>(`${API_BASE}/admin/users/overview`, { params: httpParams }).pipe(
      map((r) => {
        const youths = (r.youths as Record<string, unknown>[] | undefined) ?? [];
        const professionals = (r.professionals as Record<string, unknown>[] | undefined) ?? [];
        const meta = r.meta as Record<string, unknown> | undefined;
        const metaYouth = meta?.youths as Record<string, unknown> | undefined;
        const metaPros = meta?.professionals as Record<string, unknown> | undefined;
        return {
          youths: youths.map((y) => {
            const ap = y.assigned_professional as Record<string, unknown> | undefined;
            return {
              id: str(y.id),
              user_id: y.user_id != null ? str(y.user_id) : undefined,
              display_name: (y.display_name as string) ?? '',
              identifier: y.identifier as string | undefined,
              rut: y.rut as string | undefined,
              email: y.email as string | undefined,
              profile_photo_url: y.profile_photo_url as string | undefined,
              login_enabled: (y.login_enabled as boolean) ?? false,
              is_active: (y.is_active as boolean) ?? true,
              login_type: (y.login_type as string) ?? '',
              last_login_at: y.last_login_at as string | undefined,
              last_interview_at: y.last_interview_at as string | undefined,
              last_interview_status: y.last_interview_status as string | undefined,
              last_interview_mode: y.last_interview_mode as string | undefined,
              assigned_professional: ap
                ? {
                    id: str(ap.id),
                    display_name: (ap.display_name as string) ?? '',
                    email: ap.email as string | undefined,
                    is_active: (ap.is_active as boolean) ?? true,
                  }
                : undefined,
            };
          }),
          professionals: professionals.map((p) => ({
            id: str(p.id),
            user_id: str(p.user_id),
            display_name: (p.display_name as string) ?? '',
            email: p.email as string | undefined,
            is_active: (p.is_active as boolean) ?? true,
            login_type: (p.login_type as string) ?? '',
            last_login_at: p.last_login_at as string | undefined,
          })),
          meta: meta
            ? {
                youths: metaYouth
                  ? {
                      total: Number(metaYouth.total) || 0,
                      page: Number(metaYouth.page) || 1,
                      page_size: Number(metaYouth.page_size) || 0,
                    }
                  : undefined,
                professionals: metaPros
                  ? {
                      total: Number(metaPros.total) || 0,
                      page: Number(metaPros.page) || 1,
                      page_size: Number(metaPros.page_size) || 0,
                    }
                  : undefined,
              }
            : undefined,
        };
      }),
      catchError(() => of({ youths: [], professionals: [], meta: undefined }))
    );
  }

  /** Admin: elimina de forma logica un joven y libera su email. */
  deleteYouthAsAdmin(youthId: string): Observable<{ ok: true } | { error: string }> {
    return this.http.delete<Record<string, unknown>>(`${API_BASE}/admin/youths/${youthId}`).pipe(
      map(() => ({ ok: true as const })),
      catchError((err) => {
        const d = err.error?.detail;
        const msg = typeof d === 'string' ? d : 'Error al eliminar joven';
        return of({ error: withRequestId(msg, err) });
      })
    );
  }

  /** Admin: elimina definitivamente un joven y toda su data asociada. */
  deleteYouthHardAsAdmin(youthId: string): Observable<{ ok: true } | { error: string }> {
    return this.http.delete<Record<string, unknown>>(`${API_BASE}/admin/youths/${youthId}/hard`).pipe(
      map(() => ({ ok: true as const })),
      catchError((err) => {
        const d = err.error?.detail;
        const msg = typeof d === 'string' ? d : 'Error al eliminar definitivamente';
        return of({ error: withRequestId(msg, err) });
      })
    );
  }

  /** Admin: logs históricos del joven (accesos y entrevistas). */
  getAdminYouthLogs(
    youthId: string,
    params?: {
      platform_page?: number;
      platform_page_size?: number;
      interviews_page?: number;
      interviews_page_size?: number;
    }
  ): Observable<AdminYouthLogs> {
    let httpParams = new HttpParams();
    if (params?.platform_page) httpParams = httpParams.set('platform_page', String(params.platform_page));
    if (params?.platform_page_size) httpParams = httpParams.set('platform_page_size', String(params.platform_page_size));
    if (params?.interviews_page) httpParams = httpParams.set('interviews_page', String(params.interviews_page));
    if (params?.interviews_page_size) httpParams = httpParams.set('interviews_page_size', String(params.interviews_page_size));
    return this.http.get<Record<string, unknown>>(`${API_BASE}/admin/youths/${youthId}/logs`, { params: httpParams }).pipe(
      map((r) => {
        const platform = (r.platform_sessions as Record<string, unknown>[] | undefined) ?? [];
        const interviews = (r.interviews as Record<string, unknown>[] | undefined) ?? [];
        const meta = r.meta as Record<string, unknown> | undefined;
        const metaPlatform = meta?.platform as Record<string, unknown> | undefined;
        const metaInterviews = meta?.interviews as Record<string, unknown> | undefined;
        return {
          platform_sessions: platform.map((p) => ({
            started_at: p.started_at as string,
            ended_at: p.ended_at as string | undefined,
          })),
          interviews: interviews.map((s) => ({
            id: str(s.id),
            started_at: s.started_at as string,
            ended_at: s.ended_at as string | undefined,
            status: s.status as SessionStatus,
            mode: s.mode as SessionMode,
            professional_id: s.professional_id != null ? str(s.professional_id) : undefined,
            professional_name: s.professional_name as string | undefined,
          })),
          meta: meta
            ? {
                platform: metaPlatform
                  ? {
                      total: Number(metaPlatform.total) || 0,
                      page: Number(metaPlatform.page) || 1,
                      page_size: Number(metaPlatform.page_size) || 0,
                    }
                  : undefined,
                interviews: metaInterviews
                  ? {
                      total: Number(metaInterviews.total) || 0,
                      page: Number(metaInterviews.page) || 1,
                      page_size: Number(metaInterviews.page_size) || 0,
                    }
                  : undefined,
              }
            : undefined,
        };
      }),
      catchError(() => of({ platform_sessions: [], interviews: [], meta: undefined }))
    );
  }

  /** Admin: auditoría global de acciones (mutaciones). */
  getAuditLogs(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    action?: string;
    entity_type?: string;
    status_code?: number;
    actor_user_id?: number;
    method?: string;
  }): Observable<PagedResult<AuditLogRow>> {
    let httpParams = new HttpParams();
    if (params?.page) httpParams = httpParams.set('page', String(params.page));
    if (params?.page_size) httpParams = httpParams.set('page_size', String(params.page_size));
    if (params?.search?.trim()) httpParams = httpParams.set('search', params.search.trim());
    if (params?.action) httpParams = httpParams.set('action', params.action);
    if (params?.entity_type) httpParams = httpParams.set('entity_type', params.entity_type);
    if (params?.status_code) httpParams = httpParams.set('status_code', String(params.status_code));
    if (params?.actor_user_id) httpParams = httpParams.set('actor_user_id', String(params.actor_user_id));
    if (params?.method) httpParams = httpParams.set('method', params.method);
    return this.http.get<Record<string, unknown>>(`${API_BASE}/admin/audit-logs`, { params: httpParams }).pipe(
      map((r) => {
        const itemsRaw = (r.items as Record<string, unknown>[] | undefined) ?? [];
        const meta = r.meta as Record<string, unknown> | undefined;
        const total = Number(meta?.total) || itemsRaw.length;
        const page = Number(meta?.page) || params?.page || 1;
        const pageSize = Number(meta?.page_size) || params?.page_size || itemsRaw.length;
        const items = itemsRaw.map((log) => ({
          id: str(log.id),
          request_id: log.request_id as string | undefined,
          actor_user_id: log.actor_user_id != null ? str(log.actor_user_id) : undefined,
          actor_role: log.actor_role as string | undefined,
          actor_email: log.actor_email as string | undefined,
          action: (log.action as string) ?? '',
          entity_type: log.entity_type as string | undefined,
          entity_id: log.entity_id as string | undefined,
          status_code: Number(log.status_code) || 0,
          method: (log.method as string) ?? '',
          path: (log.path as string) ?? '',
          ip_address: log.ip_address as string | undefined,
          user_agent: log.user_agent as string | undefined,
          created_at: (log.created_at as string) ?? '',
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
          jobRoles: this.getJobRoles(),
          cases: this.getCases(),
          templates: this.getSimulationTemplates(),
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
          jobRoles: this.getJobRoles(),
          cases: this.getCases(),
          templates: this.getSimulationTemplates(),
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

  getSession(id: string): Observable<Session | null> {
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
      catchError(() => of(null))
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
  } | null> {
    return this.http
      .post<{
        session_id: number;
        liveavatar_session_id: string;
        livekit_url?: string;
        access_token?: string;
        embed?: { type: string; url: string };
      }>(`${API_BASE}/sessions/${id}/start`, {})
      .pipe(
        map((r) => ({
          session_id: str(r.session_id),
          liveavatar_session_id: r.liveavatar_session_id,
          livekit_url: r.livekit_url,
          access_token: r.access_token,
          embed: r.embed ? { type: 'iframe' as const, url: r.embed.url } : undefined,
        })),
        catchError(() => of(null))
      );
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

  getProfessionals(): Observable<{ id: string; user_id: string; display_name: string; specialty?: string; institution?: string; is_active: boolean; created_at: string; updated_at: string }[]> {
    return this.http
      .get<unknown[]>(`${API_BASE}/professionals`)
      .pipe(
        map((list) =>
          ((list || []) as Record<string, unknown>[]).map((p) => ({
            id: str(p.id),
            user_id: str(p.user_id),
            display_name: (p.display_name as string) ?? '',
            specialty: p.specialty as string | undefined,
            institution: p.institution as string | undefined,
            is_active: (p.is_active as boolean) ?? true,
            created_at: (p.created_at as string) ?? '',
            updated_at: (p.updated_at as string) ?? '',
          }))
        ),
        catchError(() => of([]))
      );
  }

  getProfessionalsPaged(params?: { page?: number; page_size?: number }): Observable<PagedResult<{ id: string; user_id: string; display_name: string; specialty?: string; institution?: string; is_active: boolean; created_at: string; updated_at: string }>> {
    let httpParams = new HttpParams();
    if (params?.page) httpParams = httpParams.set('page', String(params.page));
    if (params?.page_size) httpParams = httpParams.set('page_size', String(params.page_size));
    return this.http.get<unknown[]>(`${API_BASE}/professionals`, { params: httpParams, observe: 'response' }).pipe(
      map((res) => {
        const list = (res.body || []) as Record<string, unknown>[];
        const total = Number(res.headers.get('X-Total-Count')) || list.length;
        const page = Number(res.headers.get('X-Page')) || params?.page || 1;
        const pageSize = Number(res.headers.get('X-Page-Size')) || params?.page_size || list.length;
        const items = list.map((p) => ({
          id: str(p.id),
          user_id: str(p.user_id),
          display_name: (p.display_name as string) ?? '',
          specialty: p.specialty as string | undefined,
          institution: p.institution as string | undefined,
          is_active: (p.is_active as boolean) ?? true,
          created_at: (p.created_at as string) ?? '',
          updated_at: (p.updated_at as string) ?? '',
        }));
        return { items, total, page, page_size: pageSize };
      }),
      catchError(() => of({ items: [], total: 0, page: params?.page || 1, page_size: params?.page_size || 0 }))
    );
  }

  getProfessional(
    id: string
  ): Observable<{ id: string; user_id: string; display_name: string; specialty?: string; institution?: string; is_active: boolean; created_at: string; updated_at: string } | null> {
    return this.http
      .get<Record<string, unknown>>(`${API_BASE}/professionals/${id}`)
      .pipe(
        map((p) =>
          p
            ? {
                id: str(p.id),
                user_id: str(p.user_id),
                display_name: (p.display_name as string) ?? '',
                specialty: p.specialty as string | undefined,
                institution: p.institution as string | undefined,
                is_active: (p.is_active as boolean) ?? true,
                created_at: (p.created_at as string) ?? '',
                updated_at: (p.updated_at as string) ?? '',
              }
            : null
        ),
        catchError(() => of(null))
      );
  }

  createProfessional(data: {
    email: string;
    password: string;
    display_name: string;
    specialty?: string;
    institution?: string;
  }): Observable<{ id: string; user_id: string; display_name: string } | { error: string }> {
    return this.http
      .post<Record<string, unknown>>(`${API_BASE}/professionals`, data)
      .pipe(
        map((r) => ({
          id: str(r.id),
          user_id: str(r.user_id),
          display_name: r.display_name as string,
        })),
        catchError((err) => {
          const d = err.error?.detail;
          const msg = typeof d === 'string' ? d : 'Error al crear tutor';
          return of({ error: withRequestId(msg, err) });
        })
      );
  }

  updateProfessional(
    id: string,
    data: { display_name: string; specialty?: string; institution?: string; is_active?: boolean }
  ): Observable<{ id: string; user_id: string; display_name: string } | { error: string }> {
    return this.http
      .put<Record<string, unknown>>(`${API_BASE}/professionals/${id}`, data)
      .pipe(
        map((r) => ({
          id: str(r.id),
          user_id: str(r.user_id),
          display_name: r.display_name as string,
        })),
        catchError((err) => {
          const d = err.error?.detail;
          const msg = typeof d === 'string' ? d : 'Error al actualizar tutor';
          return of({ error: withRequestId(msg, err) });
        })
      );
  }

  uploadFile(file: File): Observable<{ url: string } | { error: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http
      .post<{ url: string }>(`${API_BASE}/upload`, formData)
      .pipe(
        map((r) => ({ url: r.url })),
        catchError((err) => {
          const d = err.error?.detail;
          const msg = typeof d === 'string' ? d : 'Error al subir archivo';
          return of({ error: withRequestId(msg, err) });
        })
      );
  }

  createSupportMaterial(data: {
    title: string;
    description?: string;
    type: MaterialType;
    url: string;
    job_role_id?: string;
    case_id?: string;
  }): Observable<SupportMaterial | { error: string }> {
    const body: Record<string, unknown> = {
      title: data.title,
      description: data.description,
      type: data.type,
      url: data.url,
    };
    if (data.job_role_id) body.job_role_id = Number(data.job_role_id);
    if (data.case_id) body.case_id = Number(data.case_id);
    return this.http
      .post<Record<string, unknown>>(`${API_BASE}/support-material`, body)
      .pipe(
        map((m) => ({
          id: str(m.id),
          title: m.title as string,
          description: m.description as string | undefined,
          type: m.type as MaterialType,
          url: m.url as string,
          job_role_id: m.job_role_id != null ? str(m.job_role_id) : undefined,
          case_id: m.case_id != null ? str(m.case_id) : undefined,
          active: (m.active as boolean) ?? true,
          created_at: '',
          updated_at: '',
        })),
        catchError((err) => {
          const d = err.error?.detail;
          const msg = typeof d === 'string' ? d : 'Error al crear material';
          return of({ error: withRequestId(msg, err) });
        })
      );
  }

  getSupportMaterial(params?: { job_role_id?: string; case_id?: string }): Observable<SupportMaterial[]> {
    let httpParams = new HttpParams();
    if (params?.job_role_id) httpParams = httpParams.set('job_role_id', params.job_role_id);
    if (params?.case_id) httpParams = httpParams.set('case_id', params.case_id);
    return this.http.get<unknown[]>(`${API_BASE}/support-material`, { params: httpParams }).pipe(
      map((list) =>
        ((list || []) as Record<string, unknown>[]).map((m) => ({
          id: str(m.id),
          title: m.title as string,
          description: m.description as string | undefined,
          type: m.type as MaterialType,
          url: m.url as string,
          job_role_id: m.job_role_id != null ? str(m.job_role_id) : undefined,
          case_id: m.case_id != null ? str(m.case_id) : undefined,
          active: (m.active as boolean) ?? true,
          created_at: '',
          updated_at: '',
        }))
      )
    );
  }

  getSupportMaterialPaged(params?: {
    job_role_id?: string;
    case_id?: string;
    page?: number;
    page_size?: number;
  }): Observable<PagedResult<SupportMaterial>> {
    let httpParams = new HttpParams();
    if (params?.job_role_id) httpParams = httpParams.set('job_role_id', params.job_role_id);
    if (params?.case_id) httpParams = httpParams.set('case_id', params.case_id);
    if (params?.page) httpParams = httpParams.set('page', String(params.page));
    if (params?.page_size) httpParams = httpParams.set('page_size', String(params.page_size));
    return this.http.get<unknown[]>(`${API_BASE}/support-material`, { params: httpParams, observe: 'response' }).pipe(
      map((res) => {
        const list = (res.body || []) as Record<string, unknown>[];
        const total = Number(res.headers.get('X-Total-Count')) || list.length;
        const page = Number(res.headers.get('X-Page')) || params?.page || 1;
        const pageSize = Number(res.headers.get('X-Page-Size')) || params?.page_size || list.length;
        const items = list.map((m) => ({
          id: str(m.id),
          title: m.title as string,
          description: m.description as string | undefined,
          type: m.type as MaterialType,
          url: m.url as string,
          job_role_id: m.job_role_id != null ? str(m.job_role_id) : undefined,
          case_id: m.case_id != null ? str(m.case_id) : undefined,
          active: (m.active as boolean) ?? true,
          created_at: '',
          updated_at: '',
        }));
        return { items, total, page, page_size: pageSize };
      }),
      catchError(() => of({ items: [], total: 0, page: params?.page || 1, page_size: params?.page_size || 0 }))
    );
  }

  suggestMaterial(data: {
    youth_id: string;
    material_id: string;
    session_id?: string;
    reason?: string;
  }): Observable<MaterialSuggestion> {
    const body = {
      youth_id: Number(data.youth_id),
      material_id: Number(data.material_id),
      session_id: data.session_id ? Number(data.session_id) : undefined,
      reason: data.reason,
    };
    return this.http
      .post<Record<string, unknown>>(`${API_BASE}/support-material/suggest`, body)
      .pipe(
        map((r) => ({
          id: str(r.id),
          youth_id: str(r.youth_id),
          material_id: str(r.material_id),
          professional_id: str(r.professional_id),
          session_id: r.session_id != null ? str(r.session_id) : undefined,
          reason: r.reason as string | undefined,
          suggested_at: (r.suggested_at as string) || new Date().toISOString(),
        }))
      );
  }

  getYouthMaterialSuggestions(youthId: string): Observable<MaterialSuggestion[]> {
    return this.http
      .get<unknown[]>(`${API_BASE}/youths/${youthId}/material-suggestions`)
      .pipe(
        map((list) =>
          ((list || []) as Record<string, unknown>[]).map((m) => ({
            id: str(m.id),
            youth_id: str(youthId),
            material_id: str(m.material_id),
            professional_id: str(m.professional_id),
            session_id: m.session_id != null ? str(m.session_id) : undefined,
            reason: m.reason as string | undefined,
            suggested_at: (m.suggested_at as string) || new Date().toISOString(),
          }))
        ),
        catchError(() => of([]))
      );
  }

  getYouthMaterialSuggestionsPaged(
    youthId: string,
    params?: { page?: number; page_size?: number }
  ): Observable<PagedResult<MaterialSuggestion & { material?: SupportMaterial | null }>> {
    let httpParams = new HttpParams();
    if (params?.page) httpParams = httpParams.set('page', String(params.page));
    if (params?.page_size) httpParams = httpParams.set('page_size', String(params.page_size));
    return this.http
      .get<unknown[]>(`${API_BASE}/youths/${youthId}/material-suggestions`, { params: httpParams, observe: 'response' })
      .pipe(
        map((res) => {
          const list = (res.body || []) as Record<string, unknown>[];
          const total = Number(res.headers.get('X-Total-Count')) || list.length;
          const page = Number(res.headers.get('X-Page')) || params?.page || 1;
          const pageSize = Number(res.headers.get('X-Page-Size')) || params?.page_size || list.length;
          const items = list.map((m) => {
            const material = m.material as Record<string, unknown> | undefined | null;
            return {
              id: str(m.id),
              youth_id: str(youthId),
              material_id: str(m.material_id),
              professional_id: str(m.professional_id),
              session_id: m.session_id != null ? str(m.session_id) : undefined,
              reason: m.reason as string | undefined,
              suggested_at: (m.suggested_at as string) || new Date().toISOString(),
              material: material
                ? {
                    id: str(material.id),
                    title: material.title as string,
                    description: material.description as string | undefined,
                    type: material.type as MaterialType,
                    url: material.url as string,
                    job_role_id: material.job_role_id != null ? str(material.job_role_id) : undefined,
                    case_id: material.case_id != null ? str(material.case_id) : undefined,
                    active: (material.active as boolean) ?? true,
                    created_at: '',
                    updated_at: '',
                  }
                : null,
            };
          });
          return { items, total, page, page_size: pageSize };
        }),
        catchError(() => of({ items: [], total: 0, page: params?.page || 1, page_size: params?.page_size || 0 }))
      );
  }

  getYouthMaterialViews(youthId: string): Observable<MaterialView[]> {
    return this.http
      .get<unknown[]>(`${API_BASE}/youths/${youthId}/material-views`)
      .pipe(
        map((list) =>
          ((list || []) as Record<string, unknown>[]).map((v) => ({
            id: str(v.id),
            youth_id: str(v.youth_id),
            material_id: str(v.material_id),
            seen_at: (v.seen_at as string) || new Date().toISOString(),
          }))
        ),
        catchError(() => of([]))
      );
  }

  getYouthMaterialViewsPaged(
    youthId: string,
    params?: { page?: number; page_size?: number }
  ): Observable<PagedResult<MaterialView>> {
    let httpParams = new HttpParams();
    if (params?.page) httpParams = httpParams.set('page', String(params.page));
    if (params?.page_size) httpParams = httpParams.set('page_size', String(params.page_size));
    return this.http
      .get<unknown[]>(`${API_BASE}/youths/${youthId}/material-views`, { params: httpParams, observe: 'response' })
      .pipe(
        map((res) => {
          const list = (res.body || []) as Record<string, unknown>[];
          const total = Number(res.headers.get('X-Total-Count')) || list.length;
          const page = Number(res.headers.get('X-Page')) || params?.page || 1;
          const pageSize = Number(res.headers.get('X-Page-Size')) || params?.page_size || list.length;
          const items = list.map((v) => ({
            id: str(v.id),
            youth_id: str(v.youth_id),
            material_id: str(v.material_id),
            seen_at: (v.seen_at as string) || new Date().toISOString(),
          }));
          return { items, total, page, page_size: pageSize };
        }),
        catchError(() => of({ items: [], total: 0, page: params?.page || 1, page_size: params?.page_size || 0 }))
      );
  }

  getYouthNotificationsPaged(
    youthId: string,
    params?: { page?: number; page_size?: number; unread_only?: boolean }
  ): Observable<YouthNotificationsPage> {
    let httpParams = new HttpParams();
    if (params?.page) httpParams = httpParams.set('page', String(params.page));
    if (params?.page_size) httpParams = httpParams.set('page_size', String(params.page_size));
    if (params?.unread_only != null) httpParams = httpParams.set('unread_only', String(params.unread_only));
    return this.http
      .get<unknown[]>(`${API_BASE}/youths/${youthId}/notifications`, { params: httpParams, observe: 'response' })
      .pipe(
        map((res) => {
          const list = (res.body || []) as Record<string, unknown>[];
          const total = Number(res.headers.get('X-Total-Count')) || list.length;
          const unread = Number(res.headers.get('X-Total-Unread')) || 0;
          const page = Number(res.headers.get('X-Page')) || params?.page || 1;
          const pageSize = Number(res.headers.get('X-Page-Size')) || params?.page_size || list.length;
          const items = list.map((n) => ({
            id: str(n.id),
            youth_id: str(n.youth_id),
            type: n.type as YouthNotificationType,
            title: n.title as string,
            message: n.message as string,
            link: n.link as string | undefined,
            entity_type: n.entity_type ? String(n.entity_type) : undefined,
            entity_id: n.entity_id != null ? str(n.entity_id) : undefined,
            created_at: (n.created_at as string) || '',
            read_at: (n.read_at as string) || null,
          }));
          return { items, total, unread, page, page_size: pageSize };
        }),
        catchError(() => of({ items: [], total: 0, unread: 0, page: params?.page || 1, page_size: params?.page_size || 0 }))
      );
  }

  markYouthNotificationsRead(youthId: string, ids: string[]): Observable<{ updated: number }> {
    const payload = { ids: ids.map((id) => Number(id)).filter((id) => !Number.isNaN(id)) };
    return this.http.patch<{ updated: number }>(`${API_BASE}/youths/${youthId}/notifications/read`, payload).pipe(
      catchError(() => of({ updated: 0 }))
    );
  }

  markAllYouthNotificationsRead(youthId: string): Observable<{ updated: number }> {
    return this.http.patch<{ updated: number }>(`${API_BASE}/youths/${youthId}/notifications/read-all`, {}).pipe(
      catchError(() => of({ updated: 0 }))
    );
  }

  recordMaterialView(materialId: string, youthId: string): Observable<MaterialView> {
    return this.http
      .post<Record<string, unknown>>(`${API_BASE}/support-material/${materialId}/view`, { youth_id: Number(youthId) })
      .pipe(
        map((r) => ({
          id: str(r.id),
          youth_id: str(r.youth_id),
          material_id: str(r.material_id),
          seen_at: (r.seen_at as string) || new Date().toISOString(),
        }))
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

  /** Lista asignaciones de un profesional. */
  getProfessionalAssignments(professionalId: string): Observable<
    { id: number; youth_id: number; professional_id: number; status: string; assigned_at: string; ended_at?: string }[]
  > {
    return this.http.get<
      { id: number; youth_id: number; professional_id: number; status: string; assigned_at: string; ended_at?: string }[]
    >(`${API_BASE}/professionals/${professionalId}/assignments`);
  }

  /** Crea asignación joven-profesional. */
  createAssignment(youthId: number, professionalId: number): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${API_BASE}/assignments`, {
      youth_id: youthId,
      professional_id: professionalId,
    });
  }

  /** Finaliza una asignación. */
  endAssignment(assignmentId: number): Observable<Record<string, unknown>> {
    return this.http.patch<Record<string, unknown>>(`${API_BASE}/assignments/${assignmentId}/end`, {});
  }
}


