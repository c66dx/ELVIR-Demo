import { HttpErrorResponse } from '@angular/common/http';

/** Mensajes por código de estado cuando el backend no devuelve detail. */
const STATUS_MESSAGES: Record<number, string> = {
  400: 'Solicitud inválida',
  401: 'Credenciales inválidas o sesión expirada',
  403: 'No tienes permiso para realizar esta acción',
  404: 'Recurso no encontrado',
  422: 'Datos inválidos',
  500: 'Error del servidor. Intenta más tarde.',
};

/**
 * Extrae un mensaje legible de HttpErrorResponse.
 * Soporta FastAPI: detail como string o array de errores de validación.
 */
export function extractErrorMessage(err: unknown, requestId?: string | null): string {
  if (!(err instanceof HttpErrorResponse)) {
    return 'Ha ocurrido un error';
  }
  const d = err.error?.detail;
  let message = '';
  if (typeof d === 'string') {
    message = d;
  } else if (Array.isArray(d) && d.length > 0) {
    const first = d[0];
    message = (first?.msg ?? first?.message ?? STATUS_MESSAGES[err.status]) ?? 'Datos inválidos';
  } else {
    message = STATUS_MESSAGES[err.status] ?? `Error ${err.status}`;
  }
  if (requestId) {
    return `${message} (Código: ${requestId})`;
  }
  return message;
}

