import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import type { SessionStatus } from '@core/models/types.model';
import type { Youth } from '@core/models/youth.model';
import { API_BASE, str, withRequestId } from '@core/services/api-http-helpers';
import type { CreateYouthResponse, PagedResult, UpdateYouthResponse, YouthWithLastSession } from '@core/services/api-types';

/**
 * CRUD y listados de jóvenes (`/youths/*`), foto de perfil.
 * Uso directo en pantallas (inyectar YouthApiService).
 */
@Injectable({ providedIn: 'root' })
export class YouthApiService {
  private http = inject(HttpClient);

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
}
