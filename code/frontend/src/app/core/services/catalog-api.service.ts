import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import type { Difficulty } from '@core/models/types.model';
import type { JobRole } from '@core/models/job-role.model';
import type { Case } from '@core/models/case.model';
import type { SimulationTemplate } from '@core/models/simulation-template.model';
import { API_BASE, str } from '@core/services/api-http-helpers';

/**
 * Catálogos de simulación: cargos, casos y plantillas cargo+caso.
 * Uso directo en pantallas (inyectar CatalogApiService).
 */
@Injectable({ providedIn: 'root' })
export class CatalogApiService {
  private http = inject(HttpClient);

  getJobRoles(): Observable<JobRole[]> {
    return this.http.get<unknown[]>(`${API_BASE}/job-roles`).pipe(
      map((list) =>
        ((list || []) as Record<string, unknown>[]).map((r) => ({
          id: str(r.id),
          slug: r.slug as string,
          name: r.name as string,
          description: r.description as string | undefined,
          objetivo: r.objetivo as string | undefined,
          area: r.area as string | undefined,
          nivel_experiencia: r.nivel_experiencia as string | undefined,
          competencias: r.competencias as string | string[] | undefined,
          tecnologias: r.tecnologias as string | string[] | undefined,
          is_active: (r.is_active as boolean) ?? true,
        })),
      ),
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
          description: c.description as string | undefined,
          intervencion_regulacion_emocional: c.intervencion_regulacion_emocional as string | undefined,
          intervencion_presentacion_personal: c.intervencion_presentacion_personal as string | undefined,
          intervencion_expectativas_empresa: c.intervencion_expectativas_empresa as string | undefined,
          is_active: (c.is_active as boolean) ?? true,
        })),
      ),
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
          }),
        ),
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
      catchError(() => of(null)),
    );
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
        catchError(() => of(null)),
      );
  }
}
