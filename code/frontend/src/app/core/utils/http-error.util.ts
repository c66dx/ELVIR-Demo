import { HttpErrorResponse } from '@angular/common/http';

/** Mensajes por código de estado cuando el backend no devuelve detail. */
const STATUS_MESSAGES: Record<number, string> = {
  400: 'Solicitud inválida',
  401: 'Credenciales inválidas o sesión expirada',
  403: 'No tienes permiso para realizar esta acción',
  404: 'Recurso no encontrado',
  422: 'Datos inválidos',
  429: 'Demasiadas solicitudes. Espera un momento e inténtalo de nuevo.',
  500: 'Error del servidor. Intenta más tarde.',
};

/** Mensajes 422 de Pydantic/email-validator suelen venir en inglés si el cliente no pasó por el backend actualizado. */
function normalizeEmailValidationMessage(msg: string): string {
  const lower = msg.toLowerCase();
  if (
    lower.includes('not a valid email') ||
    lower.includes('invalid email') ||
    (lower.includes('value is not a valid') && lower.includes('email'))
  ) {
    return 'Introduce un correo electrónico válido.';
  }
  return msg;
}

/**
 * Extrae un mensaje legible de HttpErrorResponse.
 * Soporta FastAPI: detail como string o array de errores de validación.
 */
export function extractErrorMessage(err: unknown, requestId?: string | null): string {
  if (!(err instanceof HttpErrorResponse)) {
    return 'Ha ocurrido un error';
  }

  const detail = (err.error as { detail?: unknown })?.detail;
  let message = '';

  if (typeof detail === 'string' && detail.trim()) {
    message = detail;
  } else if (err.status === 429) {
    const nested = (err.error as { error?: { message?: string } })?.error?.message;
    message =
      (typeof nested === 'string' && nested.trim() ? nested : '') ||
      STATUS_MESSAGES[429] ||
      'Demasiadas solicitudes';
  } else if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: unknown; message?: unknown } | undefined;
    const msg =
      typeof first?.msg === 'string'
        ? first.msg
        : typeof first?.message === 'string'
          ? first.message
          : '';
    message = normalizeEmailValidationMessage(msg) || STATUS_MESSAGES[err.status] || 'Datos inválidos';
  } else {
    message = STATUS_MESSAGES[err.status] || `Error ${err.status}`;
  }

  if (requestId) {
    return `${message} (Código: ${requestId})`;
  }

  return message;
}
