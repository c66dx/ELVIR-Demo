import { environment } from '../../../environments/environment';

export const API_BASE = environment.apiUrl;

/** Convierte IDs numéricos a string para compatibilidad con el frontend. */
export function str(id: unknown): string {
  return id != null ? String(id) : '';
}

export function withRequestId(message: string, err: unknown): string {
  const requestId = (err as { headers?: { get?: (name: string) => string | null } })?.headers?.get?.('X-Request-ID');
  return requestId ? `${message} (Código: ${requestId})` : message;
}
