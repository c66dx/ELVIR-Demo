import { Injectable, inject } from '@angular/core';
import { forkJoin, of, Observable } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import type { Session } from '@core/models/session.model';
import type { Youth } from '@core/models/youth.model';
import type { TranscriptResponse } from '@core/models/transcript.model';
import type { InterviewSummary } from '@core/models/interview-summary.model';
import type { SessionEvent } from '@core/models/session-event.model';
import type { SessionAudio } from '@core/models/session-audio.model';
import { SessionApiService } from '@core/services/session-api.service';
import { YouthApiService } from '@core/services/youth-api.service';

export interface SessionExtras {
  context: { jobRoleName: string; caseName: string } | null;
  transcript: TranscriptResponse | null;
  summary: InterviewSummary | null;
  events: SessionEvent[];
  competencies: { competency: string; level: string; comment: string | null }[];
  audio: SessionAudio | null;
}

interface SessionCompetencyResponse {
  session_id: number;
  items: {
    competency: { slug: string; name: string };
    level: { slug: string; label: string };
    comment: string | null;
  }[];
}

@Injectable({ providedIn: 'root' })
export class SessionDetailFacade {
  private sessions = inject(SessionApiService);
  private youths = inject(YouthApiService);

  getSession(sessionId: string): Observable<Session> {
    return this.sessions.getSession(sessionId);
  }

  getYouth(youthId: string): Observable<Youth | null> {
    return this.youths.getYouth(youthId);
  }

  getSessionExtras(sessionId: string): Observable<SessionExtras> {
    return forkJoin({
      context: this.sessions.getSessionContext(sessionId).pipe(catchError(() => of(null))),
      transcript: this.sessions.getSessionTranscript(sessionId).pipe(catchError(() => of(null))),
      summary: this.sessions.getSessionSummary(sessionId).pipe(catchError(() => of(null))),
      audio: this.sessions.getSessionAudio(sessionId).pipe(catchError(() => of(null))),
      events: this.sessions.getSessionEvents(sessionId).pipe(catchError(() => of([]))),
      competencies: this.sessions
        .getSessionCompetencies(sessionId)
        .pipe(catchError(() => of({ session_id: 0, items: [] } as SessionCompetencyResponse))),
    }).pipe(
      map(({ context, transcript, summary, audio, events, competencies }) => {
        const mapped = (competencies?.items ?? []).map((item) => ({
          competency: item.competency.name || item.competency.slug,
          level: item.level.label || item.level.slug,
          comment: item.comment ?? null,
        }));
        return { context, transcript, summary, audio, events: events ?? [], competencies: mapped };
      })
    );
  }

  saveSummary(
    sessionId: string,
    data: { summary_text: string; competency_tags?: string[] }
  ): Observable<InterviewSummary | null> {
    return this.sessions.createSessionSummary(sessionId, data);
  }
}
