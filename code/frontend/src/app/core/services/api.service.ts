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
import type { SessionEvent } from '../models/session-event.model';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

/** Respuesta al crear joven: incluye activation_url si login_enabled. */
export type CreateYouthResponse = Youth & { activation_url?: string };

/** Respuesta al editar joven: incluye activation_url si se habilita login y no tiene user_id. */
export type UpdateYouthResponse = Youth & { activation_url?: string };

export interface YouthWithLastSession extends Youth {
  status_label?: string;
  last_session?: Pick<Session, 'id' | 'status' | 'started_at' | 'ended_at'>;
}

const API_BASE = environment.apiUrl;

/** Convierte IDs numéricos a string para compatibilidad con el frontend. */
function str(id: unknown): string {
  return id != null ? String(id) : '';
}

/** Servicio HTTP para la API REST de ELVIR. Métodos para auth, jóvenes, sesiones, catálogos, material. */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  private headers(): Record<string, string> {
    const token = this.auth.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  login(email: string, password: string): Observable<{ access_token: string; role: Role; user_id: string } | { error: string }> {
    return this.http
      .post<{ access_token: string; role: string; user_id: number }>(`${API_BASE}/auth/login`, { email, password })
      .pipe(
        map((r) => ({ access_token: r.access_token, role: r.role as Role, user_id: str(r.user_id) })),
        catchError((err) => {
          const d = err.error?.detail;
          const msg = typeof d === 'string' ? d : Array.isArray(d) ? d[0]?.msg ?? 'Credenciales inválidas' : 'Credenciales inválidas';
          return of({ error: msg });
        })
      );
  }

  getMe(): Observable<{ user_id: string; role: Role; email: string; professional_id?: string; youth_id?: string } | null> {
    return this.http
      .get<{ user_id: number; role: string; email: string; professional_id?: number; youth_id?: number }>(`${API_BASE}/auth/me`, { headers: this.headers() })
      .pipe(
        map((r) => ({
          user_id: str(r.user_id),
          role: r.role as Role,
          email: r.email,
          professional_id: r.professional_id != null ? str(r.professional_id) : undefined,
          youth_id: r.youth_id != null ? str(r.youth_id) : undefined,
        })),
        catchError(() => of(null))
      );
  }

  getJobRoles(): Observable<JobRole[]> {
    return this.http.get<unknown[]>(`${API_BASE}/job-roles`, { headers: this.headers() }).pipe(
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
    return this.http.get<unknown[]>(`${API_BASE}/cases`, { headers: this.headers() }).pipe(
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
      .get<unknown[]>(`${API_BASE}/simulation-templates`, { headers: this.headers(), params: httpParams })
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
    return this.http.get<Record<string, unknown>>(`${API_BASE}/simulation-templates/${id}`, { headers: this.headers() }).pipe(
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
      .get<{ jobRoleName: string; caseName: string }>(`${API_BASE}/sessions/${sessionId}/context`, { headers: this.headers() })
      .pipe(catchError(() => of(null)));
  }

  resolveSimulationTemplate(job_role_id: string): Observable<SimulationTemplate | null> {
    return this.http
      .get<Record<string, unknown>>(`${API_BASE}/simulation-templates/resolve`, {
        headers: this.headers(),
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

  getYouths(): Observable<YouthWithLastSession[]> {
    return this.http.get<unknown[]>(`${API_BASE}/youths`, { headers: this.headers() }).pipe(
      map((list) =>
        ((list || []) as Record<string, unknown>[]).map((y) => {
          const ls = y.last_session as Record<string, unknown> | undefined;
          return {
            id: str(y.id),
            display_name: y.display_name as string,
            identifier: y.identifier as string | undefined,
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

  createYouth(data: Omit<Youth, 'id' | 'created_at' | 'updated_at'> & { email?: string }): Observable<CreateYouthResponse> {
    const body: Record<string, unknown> = {
      display_name: data.display_name,
      identifier: data.identifier,
      phone: data.phone,
      login_enabled: data.login_enabled,
      general_notes: data.general_notes,
      profile_checklist: data.profile_checklist,
    };
    if (data.email) body.email = data.email;
    return this.http.post<Record<string, unknown>>(`${API_BASE}/youths`, body, { headers: this.headers() }).pipe(
      map((y) => ({
        id: str(y.id),
        display_name: y.display_name as string,
        identifier: y.identifier as string | undefined,
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

  validateActivationToken(token: string): Observable<{ valid: boolean; email?: string; display_name?: string; error?: string }> {
    return this.http
      .get<{ valid: boolean; email?: string; display_name?: string; error?: string }>(`${API_BASE}/auth/activate/validate`, {
        params: { token },
      })
      .pipe(catchError(() => of({ valid: false, error: 'TOKEN_NOT_FOUND' })));
  }

  activateAccount(token: string, password: string): Observable<{ success: boolean; error?: string }> {
    return this.http.post<{ success: boolean; error?: string }>(`${API_BASE}/auth/activate`, { token, password }).pipe(
      map((r) => ({ success: r.success, error: r.error })),
      catchError((err) => of({ success: false, error: err.error?.error ?? 'TOKEN_NOT_FOUND' }))
    );
  }

  getYouth(id: string): Observable<Youth | null> {
    return this.http.get<Record<string, unknown>>(`${API_BASE}/youths/${id}`, { headers: this.headers() }).pipe(
      map((y) => ({
        id: str(y.id),
        display_name: y.display_name as string,
        identifier: y.identifier as string | undefined,
        phone: y.phone as string | undefined,
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
    return this.http.put<Record<string, unknown>>(`${API_BASE}/youths/${id}`, body, { headers: this.headers() }).pipe(
      map((y) => ({
        id: str(y.id),
        display_name: y.display_name as string,
        identifier: y.identifier as string | undefined,
        phone: y.phone as string | undefined,
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
    return this.http.patch<void>(`${API_BASE}/youths/${id}/deactivate`, {}, { headers: this.headers() });
  }

  activateYouth(id: string): Observable<void> {
    return this.http.patch<void>(`${API_BASE}/youths/${id}/activate`, {}, { headers: this.headers() });
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
    return this.http.post<Record<string, unknown>>(`${API_BASE}/sessions`, body, { headers: this.headers() }).pipe(
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
      .get<unknown[]>(`${API_BASE}/sessions/${sessionId}/events`, { headers: this.headers() })
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
    return this.http.get<unknown[]>(`${API_BASE}/sessions`, { headers: this.headers(), params: httpParams }).pipe(
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

  getSession(id: string): Observable<Session | null> {
    return this.http.get<Record<string, unknown>>(`${API_BASE}/sessions/${id}`, { headers: this.headers() }).pipe(
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
      }>(`${API_BASE}/sessions/${id}/start`, {}, { headers: this.headers() })
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
      .post<Record<string, unknown>>(`${API_BASE}/sessions/${id}/close`, body, { headers: this.headers() })
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

  getProfessionals(): Observable<{ id: string; user_id: string; display_name: string; specialty?: string; institution?: string; is_active: boolean }[]> {
    return this.http
      .get<unknown[]>(`${API_BASE}/professionals`, { headers: this.headers() })
      .pipe(
        map((list) =>
          ((list || []) as Record<string, unknown>[]).map((p) => ({
            id: str(p.id),
            user_id: str(p.user_id),
            display_name: (p.display_name as string) ?? '',
            specialty: p.specialty as string | undefined,
            institution: p.institution as string | undefined,
            is_active: (p.is_active as boolean) ?? true,
          }))
        ),
        catchError(() => of([]))
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
      .post<Record<string, unknown>>(`${API_BASE}/professionals`, data, { headers: this.headers() })
      .pipe(
        map((r) => ({
          id: str(r.id),
          user_id: str(r.user_id),
          display_name: r.display_name as string,
        })),
        catchError((err) => {
          const d = err.error?.detail;
          const msg = typeof d === 'string' ? d : 'Error al crear profesional';
          return of({ error: msg });
        })
      );
  }

  uploadFile(file: File): Observable<{ url: string } | { error: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http
      .post<{ url: string }>(`${API_BASE}/upload`, formData, { headers: this.headers() })
      .pipe(
        map((r) => ({ url: r.url })),
        catchError((err) => {
          const d = err.error?.detail;
          const msg = typeof d === 'string' ? d : 'Error al subir archivo';
          return of({ error: msg });
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
      .post<Record<string, unknown>>(`${API_BASE}/support-material`, body, { headers: this.headers() })
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
          return of({ error: msg });
        })
      );
  }

  getSupportMaterial(params?: { job_role_id?: string; case_id?: string }): Observable<SupportMaterial[]> {
    let httpParams = new HttpParams();
    if (params?.job_role_id) httpParams = httpParams.set('job_role_id', params.job_role_id);
    if (params?.case_id) httpParams = httpParams.set('case_id', params.case_id);
    return this.http.get<unknown[]>(`${API_BASE}/support-material`, { headers: this.headers(), params: httpParams }).pipe(
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
      .post<Record<string, unknown>>(`${API_BASE}/support-material/suggest`, body, { headers: this.headers() })
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
      .get<unknown[]>(`${API_BASE}/youths/${youthId}/material-suggestions`, { headers: this.headers() })
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

  getYouthMaterialViews(youthId: string): Observable<MaterialView[]> {
    return this.http
      .get<unknown[]>(`${API_BASE}/youths/${youthId}/material-views`, { headers: this.headers() })
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

  recordMaterialView(materialId: string, youthId: string): Observable<MaterialView> {
    return this.http
      .post<Record<string, unknown>>(`${API_BASE}/support-material/${materialId}/view`, { youth_id: Number(youthId) }, { headers: this.headers() })
      .pipe(
        map((r) => ({
          id: str(r.id),
          youth_id: str(r.youth_id),
          material_id: str(r.material_id),
          seen_at: (r.seen_at as string) || new Date().toISOString(),
        }))
      );
  }

  getSessionSummary(sessionId: string): Observable<InterviewSummary | null> {
    return this.http
      .get<Record<string, unknown>>(`${API_BASE}/sessions/${sessionId}/summary`, { headers: this.headers() })
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
      .post<Record<string, unknown>>(`${API_BASE}/sessions/${sessionId}/summary`, data, { headers: this.headers() })
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
}
