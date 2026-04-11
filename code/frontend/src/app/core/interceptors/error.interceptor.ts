import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { NotificationService } from '@core/services/notification.service';
import { extractErrorMessage } from '@core/utils/http-error.util'; 
 /** URLs donde el componente maneja el error (evitar toast duplicado). */
const SKIP_TOAST_URLS = ['/auth/login', '/auth/activate', '/auth/logout', '/auth/change-password'];
const SKIP_TOAST_PATTERNS = [/\/sessions\/[^/]+\/audio/]; 
 /**   * Interceptor que muestra un toast de error ante fallos HTTP.   * Omite login/activate (el componente muestra el error en el formulario).   */
export const errorInterceptor: HttpInterceptorFn = (req, next) => { 
 const notification = inject(NotificationService); 
 return next(req).pipe(   catchError((err) => { 
 const skip =   SKIP_TOAST_URLS.some((u) => req.url.includes(u)) ||   SKIP_TOAST_PATTERNS.some((pattern) => pattern.test(req.url)); 
 if (!skip) { 
 const requestId = err?.headers?.get?.('X-Request-ID')  ?? null; 
 notification.error(extractErrorMessage(err, requestId)); 
 } 
 return throwError(() => err); 
 })   );
};
