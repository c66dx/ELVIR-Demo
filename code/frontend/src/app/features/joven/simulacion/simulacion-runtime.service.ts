import { Injectable } from '@angular/core';
import type { Session } from '../../../core/models/session.model';
import type { SessionStatus } from '../../../core/models/types.model';
import type { SessionEndData } from '../../../core/services/session-end.service';

export interface SessionContextInfo {
  jobRoleName?: string;
  caseName?: string;
}

@Injectable({ providedIn: 'root' })
export class SimulacionRuntimeService {
  private startTime: number | null = null;
  private timerInterval: ReturnType<typeof setInterval> | null = null;

  startTimer(onTick: (value: string) => void): void {
    this.stopTimer();
    this.startTime = Date.now();
    onTick('0:00');
    this.timerInterval = setInterval(() => {
      onTick(this.getElapsedLabel());
    }, 1000);
  }

  stopTimer(): void {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  getDurationSeconds(): number | undefined {
    if (!this.startTime) return undefined;
    return Math.floor((Date.now() - this.startTime) / 1000);
  }

  buildCloseMetrics(status: SessionStatus): Record<string, unknown> | undefined {
    if (status !== 'COMPLETADA') return undefined;
    const durationSec = this.getDurationSeconds();
    return { duration_seconds: durationSec };
  }

  buildSessionEndData(params: {
    status: SessionStatus;
    motivo?: string;
    returnUrl?: string;
    youthId?: string;
    session: Session | null;
    context: SessionContextInfo | null;
    sessionId: string;
  }): SessionEndData {
    const shouldAttachSummary = params.status === 'COMPLETADA' && (params.session?.duration_seconds || params.context);
    return {
      status: params.status,
      motivo: params.motivo,
      returnUrl: params.returnUrl,
      youthId: params.youthId,
      sessionSummary: shouldAttachSummary
        ? {
            duration_seconds: params.session?.duration_seconds,
            jobRoleName: params.context?.jobRoleName,
            caseName: params.context?.caseName,
            sessionId: params.sessionId,
          }
        : undefined,
    };
  }

  private getElapsedLabel(): string {
    if (!this.startTime) return '0:00';
    const sec = Math.floor((Date.now() - this.startTime) / 1000);
    const minutes = Math.floor(sec / 60);
    const seconds = sec % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }
}
