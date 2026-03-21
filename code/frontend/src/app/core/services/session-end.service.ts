import { Injectable } from '@angular/core';
import type { SessionStatus } from '../models/types.model';

/**
 * Servicio para pasar datos de la sesión finalizada a la pantalla session-end.
 * Se usa porque la navegación a /session-end no permite pasar estado por URL.
 */
export interface SessionEndData {
  status: SessionStatus;
  motivo?: string;
  returnUrl?: string;
  youthId?: string;
  /** Métricas y contexto para mostrar resumen al joven */
  sessionSummary?: {
    duration_seconds?: number;
    jobRoleName?: string;
    caseName?: string;
    sessionId?: string;
  };
}

@Injectable({ providedIn: 'root' })
export class SessionEndService {
  private data: SessionEndData | null = null;

  set(data: SessionEndData): void {
    this.data = data;
  }

  get(): SessionEndData | null {
    return this.data;
  }

  clear(): void {
    this.data = null;
  }
}

