import { Injectable, inject } from '@angular/core';
import { forkJoin, of } from 'rxjs';
import { map } from 'rxjs/operators';
import type { InterviewSummary } from '@core/models/interview-summary.model';
import type { SessionWithTemplateLabel } from '@core/services/api-types';
import { SessionApiService } from '@core/services/session-api.service';

@Injectable({ providedIn: 'root' })
export class HistorialJovenFacade {
  private sessions = inject(SessionApiService);

  getSessionsPage(youthId: string, page: number, pageSize: number) {
    return this.sessions.getSessionsWithTemplateLabelPaged({
      youth_id: youthId,
      page,
      page_size: pageSize,
    });
  }

  getSessionSummariesMap(sessions: SessionWithTemplateLabel[]) {
    if (sessions.length === 0) {
      return of(new Map<string, InterviewSummary>());
    }
    return forkJoin(sessions.map((s) => this.sessions.getSessionSummary(s.id))).pipe(
      map((summaries) => {
        const mapBySession = new Map<string, InterviewSummary>();
        summaries.forEach((summary) => {
          if (summary) mapBySession.set(summary.session_id, summary);
        });
        return mapBySession;
      })
    );
  }
}
