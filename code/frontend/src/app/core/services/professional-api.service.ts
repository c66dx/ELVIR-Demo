import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { API_BASE, str, withRequestId } from '@core/services/api-http-helpers';
import type { PagedResult } from '@core/services/api-types';

export interface ProfessionalListItem {
  id: string;
  user_id: string;
  display_name: string;
  specialty?: string;
  institution?: string;
  is_active: boolean;
  profile_photo_url?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Tutores (`/professionals/*`) y asignaciones joven–profesional (`/assignments`).
 * Uso directo en pantallas (inyectar ProfessionalApiService).
 */
@Injectable({ providedIn: 'root' })
export class ProfessionalApiService {
  private http = inject(HttpClient);

  getProfessionals(): Observable<ProfessionalListItem[]> {
    return this.http.get<unknown[]>(`${API_BASE}/professionals`).pipe(
      map((list) =>
        ((list || []) as Record<string, unknown>[]).map((p) => ({
          id: str(p.id),
          user_id: str(p.user_id),
          display_name: (p.display_name as string) ?? '',
          specialty: p.specialty as string | undefined,
          institution: p.institution as string | undefined,
          is_active: (p.is_active as boolean) ?? true,
          profile_photo_url: p.profile_photo_url as string | undefined,
          created_at: (p.created_at as string) ?? '',
          updated_at: (p.updated_at as string) ?? '',
        }))
      ),
      catchError(() => of([]))
    );
  }

  getProfessionalsPaged(params?: { page?: number; page_size?: number }): Observable<PagedResult<ProfessionalListItem>> {
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
          profile_photo_url: p.profile_photo_url as string | undefined,
          created_at: (p.created_at as string) ?? '',
          updated_at: (p.updated_at as string) ?? '',
        }));
        return { items, total, page, page_size: pageSize };
      }),
      catchError(() => of({ items: [], total: 0, page: params?.page || 1, page_size: params?.page_size || 0 }))
    );
  }

  getProfessional(id: string): Observable<ProfessionalListItem | null> {
    return this.http.get<Record<string, unknown>>(`${API_BASE}/professionals/${id}`).pipe(
      map((p) =>
        p
          ? {
              id: str(p.id),
              user_id: str(p.user_id),
              display_name: (p.display_name as string) ?? '',
              specialty: p.specialty as string | undefined,
              institution: p.institution as string | undefined,
              is_active: (p.is_active as boolean) ?? true,
              profile_photo_url: p.profile_photo_url as string | undefined,
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
    display_name: string;
    specialty?: string;
    institution?: string;
  }): Observable<{ id: string; user_id: string; display_name: string; activation_url?: string } | { error: string }> {
    return this.http
      .post<Record<string, unknown>>(`${API_BASE}/professionals`, data)
      .pipe(
        map((r) => ({
          id: str(r.id),
          user_id: str(r.user_id),
          display_name: r.display_name as string,
          activation_url: (r.activation_url as string | undefined) ?? (r.activationUrl as string | undefined),
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

  getProfessionalAssignments(professionalId: string): Observable<
    { id: number; youth_id: number; professional_id: number; status: string; assigned_at: string; ended_at?: string }[]
  > {
    return this.http.get<
      { id: number; youth_id: number; professional_id: number; status: string; assigned_at: string; ended_at?: string }[]
    >(`${API_BASE}/professionals/${professionalId}/assignments`);
  }

  createAssignment(youthId: number, professionalId: number): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${API_BASE}/assignments`, {
      youth_id: youthId,
      professional_id: professionalId,
    });
  }

  endAssignment(assignmentId: number): Observable<Record<string, unknown>> {
    return this.http.patch<Record<string, unknown>>(`${API_BASE}/assignments/${assignmentId}/end`, {});
  }
}
