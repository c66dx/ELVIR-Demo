import { environment } from '../../../environments/environment';

/** Origen del API (sin `/api/v1`), para montar rutas `/uploads/...` coherentes con `environment.apiUrl`. */
export function apiOriginFromEnvironment(): string {
  const raw = environment.apiUrl.replace(/\/?api\/v1\/?$/i, '').trim();
  if (!raw || raw === '/' || raw === '.') {
    if (typeof window !== 'undefined') {
      return window.location.origin;
    }
    return '';
  }
  try {
    const base = raw.endsWith('/') ? raw : `${raw}/`;
    return new URL(base).origin;
  } catch {
    return typeof window !== 'undefined' ? window.location.origin : '';
  }
}

/**
 * Alinea URLs de ficheros servidos por el API (`/uploads/...`) con el origen configurado en el front.
 * Evita roturas cuando la BD guardó `http://localhost:8000/...` y el front usa `127.0.0.1` o proxy.
 */
export function resolveUploadUrl(url: string | null | undefined): string | null {
  if (!url?.trim()) {
    return null;
  }
  const u = url.trim();
  const origin = apiOriginFromEnvironment();
  if (!origin) {
    return u;
  }
  try {
    if (u.startsWith('/')) {
      return `${origin}${u}`;
    }
    const parsed = new URL(u);
    if (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') {
      return `${origin}${parsed.pathname}${parsed.search}${parsed.hash}`;
    }
  } catch {
    return u;
  }
  return u;
}
