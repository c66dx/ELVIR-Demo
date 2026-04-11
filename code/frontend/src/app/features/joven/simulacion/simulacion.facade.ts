import { Injectable, inject } from '@angular/core';
import type { SessionStatus } from '@core/models/types.model';
import { SessionApiService } from '@core/services/session-api.service';

@Injectable({ providedIn: 'root' })
export class SimulacionFacade {
  private sessions = inject(SessionApiService);

  getSession(sessionId: string) {
    return this.sessions.getSession(sessionId);
  }

  getSessionContext(sessionId: string) {
    return this.sessions.getSessionContext(sessionId);
  }

  getSessionSummary(sessionId: string) {
    return this.sessions.getSessionSummary(sessionId);
  }

  startSession(sessionId: string) {
    return this.sessions.startSession(sessionId);
  }

  closeSession(
    sessionId: string,
    data: { status: SessionStatus; metrics?: Record<string, unknown>; motivo?: string }
  ) {
    return this.sessions.closeSession(sessionId, data);
  }

  heartbeatSession(sessionId: string) {
    return this.sessions.heartbeatSession(sessionId);
  }

  uploadSessionAudio(sessionId: string, file: File, durationSeconds?: number) {
    return this.sessions.uploadSessionAudio(sessionId, file, durationSeconds);
  }
}
