import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import type { Role } from '@core/models/types.model';
import { API_BASE, str, withRequestId } from '@core/services/api-http-helpers';

/**
 * Auth (`/auth/*`): login, logout, sesiÃ³n actual, cambio de contraseÃ±a/email, foto y activaciÃ³n.
 * Uso directo en pantallas (inyectar AuthApiService).
 */
@Injectable({ providedIn: 'root' })
export class AuthApiService {
  private http = inject(HttpClient);

  /** El AuthInterceptor aÃ±ade el token Bearer automÃ¡ticamente a las peticiones autenticadas. */
  login(email: string, password: string): Observable<{ access_token: string; role: Role; user_id: string } | { error: string }> {
    return this.http
      .post<{ access_token: string; role: string; user_id: number }>(`${API_BASE}/auth/login`, { email, password })
      .pipe(
        map((r) => ({ access_token: r.access_token, role: r.role as Role, user_id: str(r.user_id) })),
        catchError((err) => {
          const d = err.error?.detail;
          const msg = typeof d === 'string' ? d : Array.isArray(d) ? d[0]?.msg ?? 'Credenciales invÃ¡lidas' : 'Credenciales invÃ¡lidas';
          return of({ error: withRequestId(msg, err) });
        })
      );
  }

  /** Registra cierre de sesiÃ³n en backend (para mÃ©tricas de plataforma). */
  logout(): Observable<void> {
    return this.http.post<void>(`${API_BASE}/auth/logout`, {}).pipe(catchError(() => of(undefined)));
  }

  getMe(): Observable<{
    user_id: string;
    role: Role;
    email: string;
    profile_photo_url?: string;
    professional_id?: string;
    youth_id?: string;
  } | null> {
    return this.http
      .get<{ user_id: number; role: string; email: string; profile_photo_url?: string; professional_id?: number; youth_id?: number }>(
        `${API_BASE}/auth/me`
      )
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
          const msg = typeof d === 'string' ? d : 'Error al cambiar contraseÃ±a';
          return of({ error: withRequestId(msg, err) });
        })
      );
  }

  requestEmailChange(
    new_email: string,
    current_password: string
  ): Observable<{ success: true; activation_url?: string } | { error: string }> {
    return this.http
      .post<{ success: boolean; activation_url?: string }>(`${API_BASE}/auth/change-email`, {
        new_email,
        current_password,
      })
      .pipe(
        map((r) => ({ success: true as const, activation_url: r.activation_url })),
        catchError((err) => {
          const d = err.error?.detail;
          const msg = typeof d === 'string' ? d : 'Error al solicitar cambio de correo';
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

  validateActivationToken(
    token: string
  ): Observable<{ valid: boolean; email?: string; display_name?: string; error?: string; is_change_email?: boolean }> {
    return this.http
      .get<{ valid: boolean; email?: string; display_name?: string; error?: string; is_change_email?: boolean }>(
        `${API_BASE}/auth/activate/validate`,
        { params: { token } }
      )
      .pipe(catchError(() => of({ valid: false, error: 'TOKEN_NOT_FOUND' })));
  }

  activateAccount(params: { token: string; password?: string; current_password?: string }): Observable<{ success: boolean; error?: string }> {
    const body: Record<string, string> = { token: params.token };
    if (params.password != null) body.password = params.password;
    if (params.current_password != null) body.current_password = params.current_password;
    return this.http.post<{ success: boolean; error?: string }>(`${API_BASE}/auth/activate`, body).pipe(
      map((r) => ({ success: r.success, error: r.error })),
      catchError((err) => of({ success: false, error: withRequestId(err.error?.error ?? 'TOKEN_NOT_FOUND', err) }))
    );
  }
}
