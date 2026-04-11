import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, of, EMPTY } from 'rxjs';
import { map, catchError, mergeMap } from 'rxjs/operators';
import type { MaterialType } from '@core/models/types.model';
import type { SupportMaterial } from '@core/models/support-material.model';
import type { MaterialSuggestion } from '@core/models/material-suggestion.model';
import type { MaterialView } from '@core/models/material-view.model';
import { API_BASE, str, withRequestId } from '@core/services/api-http-helpers';
import type { PagedResult, YouthNotificationType, YouthNotificationsPage } from '@core/services/api-types';

/**
 * Material de apoyo, sugerencias, vistas y notificaciones del joven.
 * Uso directo en pantallas (inyectar MaterialApiService).
 */
@Injectable({ providedIn: 'root' })
export class MaterialApiService {
  private http = inject(HttpClient);

  /**
   * Subida de material (staff). Emite `{ progress: 0–100 }` durante el envío y luego `{ url }` o `{ error }`.
   */
  uploadFile(file: File): Observable<{ url: string } | { error: string } | { progress: number }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http
      .post<{ url: string }>(`${API_BASE}/upload`, formData, {
        reportProgress: true,
        observe: 'events',
      })
      .pipe(
        mergeMap((event: HttpEvent<{ url: string }>) => {
          if (event.type === HttpEventType.UploadProgress) {
            const total = event.total;
            const pct =
              total != null && total > 0 ? Math.round((100 * event.loaded) / total) : event.loaded > 0 ? -1 : 0;
            return of({ progress: pct });
          }
          if (event.type === HttpEventType.Response && event.body) {
            return of({ url: event.body.url });
          }
          return EMPTY;
        }),
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
}
