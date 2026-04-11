import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import type { SessionMode, SessionStatus } from '@core/models/types.model';
import { API_BASE, str, withRequestId } from '@core/services/api-http-helpers';
import type { PagedResult } from '@core/services/api-types';
import type { AdminUsersOverview, AdminYouthLogs, AuditLogRow } from '@core/services/admin-api.types';

/**
 * Endpoints bajo `/admin/*` (usuarios, logs, auditoría, borrados administrativos).
 * El resto del cliente HTTP vive en servicios de dominio.
 */
@Injectable({ providedIn: 'root' })
export class AdminApiService {
  private http = inject(HttpClient);

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
            profile_photo_url: p.profile_photo_url as string | undefined,
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
      catchError(() => of({ youths: [], professionals: [], meta: undefined })),
    );
  }

  deleteYouthAsAdmin(youthId: string): Observable<{ ok: true } | { error: string }> {
    return this.http.delete<Record<string, unknown>>(`${API_BASE}/admin/youths/${youthId}`).pipe(
      map(() => ({ ok: true as const })),
      catchError((err) => {
        const d = err.error?.detail;
        const msg = typeof d === 'string' ? d : 'Error al eliminar joven';
        return of({ error: withRequestId(msg, err) });
      }),
    );
  }

  deleteProfessionalAsAdmin(professionalId: string): Observable<{ ok: true } | { error: string }> {
    return this.http.delete<Record<string, unknown>>(`${API_BASE}/admin/professionals/${professionalId}`).pipe(
      map(() => ({ ok: true as const })),
      catchError((err) => {
        const d = err.error?.detail;
        const msg = typeof d === 'string' ? d : 'Error al eliminar tutor';
        return of({ error: withRequestId(msg, err) });
      }),
    );
  }

  deleteYouthHardAsAdmin(youthId: string): Observable<{ ok: true } | { error: string }> {
    return this.http.delete<Record<string, unknown>>(`${API_BASE}/admin/youths/${youthId}/hard`).pipe(
      map(() => ({ ok: true as const })),
      catchError((err) => {
        const d = err.error?.detail;
        const msg = typeof d === 'string' ? d : 'Error al eliminar definitivamente';
        return of({ error: withRequestId(msg, err) });
      }),
    );
  }

  getAdminYouthLogs(
    youthId: string,
    params?: {
      platform_page?: number;
      platform_page_size?: number;
      interviews_page?: number;
      interviews_page_size?: number;
    },
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
      catchError(() => of({ platform_sessions: [], interviews: [], meta: undefined })),
    );
  }

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
      catchError(() => of({ items: [], total: 0, page: params?.page || 1, page_size: params?.page_size || 0 })),
    );
  }
}
