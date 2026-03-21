import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

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
 * Interceptor HTTP que:
 * - Envía cookies de sesión (`withCredentials`) para auth con HttpOnly cookie.
 * - Adjunta header CSRF para métodos mutables.
 * - Mantiene compatibilidad opcional con Bearer token en memoria.
 * - Ante 401, hace logout y redirige a /login (excepto en login y activación).
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

