import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '@core/services/auth.service';

const CSRF_COOKIE_NAME = 'elvir_csrf_token';
const CSRF_HEADER_NAME = 'X-CSRF-Token';
const REQUEST_ID_HEADER = 'X-Request-ID';

function readCookie(name: string): string | null {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function generateRequestId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  const rand = Math.random().toString(16).slice(2);
  return `req-${Date.now().toString(16)}-${rand}`;
}

/**
 * Interceptor HTTP:
 * - Añade `Authorization: Bearer` si hay token en sessionStorage (flujo principal en SPA).
 * - Si existe cookie CSRF legible (`elvir_csrf_token`), la envía en mutaciones (alineado con backend).
 * - Añade `X-Request-ID` si no viene ya en la petición.
 * - `withCredentials: false`: no envía cookies HttpOnly al API en peticiones cross-origin; el CSRF del
 *   middleware solo aplica cuando el backend recibe cookie de sesión (p. ej. mismo sitio con credenciales).
 * - Ante 401: logout y /login, excepto en llamadas a login y activación de cuenta (API `/auth/login`, `/auth/activate`).
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const token = auth.getToken();
  const csrfToken = readCookie(CSRF_COOKIE_NAME);
  const isMutableMethod = req.method !== 'GET' && req.method !== 'HEAD' && req.method !== 'OPTIONS';
  const existingRequestId = req.headers.get(REQUEST_ID_HEADER);
  const requestId = existingRequestId || generateRequestId();

  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (isMutableMethod && csrfToken) headers[CSRF_HEADER_NAME] = csrfToken;
  if (!existingRequestId) headers[REQUEST_ID_HEADER] = requestId;

  const cloned = req.clone({
    withCredentials: false,
    setHeaders: headers,
  });

  return next(cloned).pipe(
    catchError((err) => {
      const isAuthEndpoint = req.url.includes('/auth/login') || req.url.includes('/auth/activate');
      if (err.status === 401 && !isAuthEndpoint) {
        auth.logout();
        router.navigate(['/login']);
      }
      return throwError(() => err);
    })
  );
};
