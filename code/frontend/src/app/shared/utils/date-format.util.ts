/**
 * Utilidades de formato para fechas, duraciones y estados de sesión.
 * Centraliza la lógica compartida entre componentes.
 */

export function formatDate(iso?: string): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('es-CL', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatDuration(seconds?: number): string {
  if (!seconds) return '-';
  if (seconds < 60) return `${seconds} s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `${m} min ${s} s` : `${m} min`;
}

/** Calcula segundos entre dos fechas ISO. */
export function durationBetween(startIso: string, endIso: string): number {
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  return Math.round((end - start) / 1000);
}

export const SESSION_STATUS_LABELS: Record<string, string> = {
  EN_CURSO: 'En curso',
  COMPLETADA: 'Completada',
  CANCELADA: 'Cancelada',
  ERROR: 'Error',
};

export function formatStatusLabel(status: string): string {
  return SESSION_STATUS_LABELS[status] ?? status;
}

