import { Injectable, inject } from '@angular/core';
import { forkJoin, of } from 'rxjs';
import { map } from 'rxjs/operators';
import type { InterviewSummary } from '@core/models/interview-summary.model';
import type { SessionWithTemplateLabel } from '@core/services/api-types';
import { MaterialApiService } from '@core/services/material-api.service';
import { SessionApiService } from '@core/services/session-api.service';
import { YouthApiService } from '@core/services/youth-api.service';

@Injectable({ providedIn: 'root' })
export class PerfilJovenFacade {
  private youths = inject(YouthApiService);
  private sessions = inject(SessionApiService);
  private materials = inject(MaterialApiService);

  loadProfileBase(youthId: string) {
    return forkJoin({
      youth: this.youths.getYouth(youthId),
      competencies: this.sessions.getCompetencies(),
      competencyLevels: this.sessions.getCompetencyLevels(),
      stats: this.sessions.getSessionStats({ youth_id: youthId, months: 6 }),
    });
  }

  uploadYouthPhoto(youthId: string, file: File) {
    return this.youths.uploadYouthPhoto(youthId, file);
  }

  getSessionsPage(youthId: string, page: number, pageSize: number) {
    return this.sessions.getSessionsWithTemplateLabelPaged({
      youth_id: youthId,
      page,
      page_size: pageSize,
    });
  }

  getPlatformPage(youthId: string, page: number, pageSize: number) {
    return this.sessions.getPlatformSessionsPaged(youthId, {
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

  getSupportMaterial() {
    return this.materials.getSupportMaterial();
  }

  suggestMaterial(data: { youth_id: string; material_id: string; reason?: string; session_id?: string }) {
    return this.materials.suggestMaterial(data);
  }

  getSessionTranscript(sessionId: string) {
    return this.sessions.getSessionTranscript(sessionId);
  }

  getSessionCompetencies(sessionId: string) {
    return this.sessions.getSessionCompetencies(sessionId);
  }

  saveSummary(sessionId: string, data: { summary_text: string; competency_tags?: string[] }) {
    return this.sessions.createSessionSummary(sessionId, data);
  }

  saveCompetencies(
    sessionId: string,
    items: { competency_slug: string; level_slug: string; comment?: string }[]
  ) {
    return this.sessions.createSessionCompetencies(sessionId, items);
  }
}
