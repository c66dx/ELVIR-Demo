import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';
import { YouthService } from '../../../core/services/youth.service';
import { ApiService } from '../../../core/services/api.service';
import type { Session } from '../../../core/models/session.model';
import type { InterviewSummary } from '../../../core/models/interview-summary.model';
import { formatDate, formatStatusLabel } from '../../../shared/utils/date-format.util';

interface FeedbackItem {
  sessionId: string;
  startedAt: string;
  status: string;
  jobRoleName?: string;
  caseName?: string;
  summaryText?: string;
  strengths: string[];
  suggestions: string[];
}

@Component({
  selector: 'app-retroalimentacion-joven',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './retroalimentacion.component.html',
  styleUrl: './retroalimentacion.component.scss',
})
export class RetroalimentacionJovenComponent {
  private youthService = inject(YouthService);
  private api = inject(ApiService);

  feedback$ = this.youthService.getCurrentYouthId().pipe(
    switchMap((youthId) => {
      if (!youthId) return of([] as FeedbackItem[]);
      return this.api.getSessions({ youth_id: youthId }).pipe(
        switchMap((sessions) => this.buildFeedbackItems(sessions)),
        catchError(() => of([] as FeedbackItem[]))
      );
    }),
    catchError(() => of([] as FeedbackItem[]))
  );

  private buildFeedbackItems(sessions: Session[]) {
    if (sessions.length === 0) return of([] as FeedbackItem[]);
    const items$ = sessions.map((session) =>
      forkJoin({
        context: this.api.getSessionContext(session.id).pipe(catchError(() => of(null))),
        summary: this.api.getSessionSummary(session.id).pipe(catchError(() => of(null))),
      }).pipe(
        map(({ context, summary }) => this.mapFeedbackItem(session, summary, context?.jobRoleName, context?.caseName))
      )
    );
    return forkJoin(items$).pipe(
      map((items) =>
        items.sort((a, b) => {
          if (!a.startedAt || !b.startedAt) return 0;
          return b.startedAt.localeCompare(a.startedAt);
        })
      )
    );
  }

  private mapFeedbackItem(
    session: Session,
    summary: InterviewSummary | null,
    jobRoleName?: string,
    caseName?: string
  ): FeedbackItem {
    const parsed = this.parseSummary(summary?.summary_text);
    return {
      sessionId: session.id,
      startedAt: session.started_at || '',
      status: session.status,
      jobRoleName,
      caseName,
      summaryText: parsed.general,
      strengths: parsed.strengths,
      suggestions: parsed.suggestions,
    };
  }

  private parseSummary(text?: string): { general: string; strengths: string[]; suggestions: string[] } {
    if (!text) {
      return { general: '', strengths: [], suggestions: [] };
    }
    const cleaned = text.replace(/\r/g, '').trim();
    const lower = cleaned.toLowerCase();
    const strengthsIndex = lower.indexOf('puntos fuertes');
    const suggestionsIndex = lower.indexOf('sugerencias');

    const firstIndex = [strengthsIndex, suggestionsIndex].filter((i) => i >= 0).sort((a, b) => a - b)[0];
    const general = firstIndex != null ? cleaned.slice(0, firstIndex).trim() : cleaned;

    const strengthsText = this.extractSection(cleaned, strengthsIndex, suggestionsIndex);
    const suggestionsText = this.extractSection(cleaned, suggestionsIndex, -1);

    return {
      general,
      strengths: this.parseList(strengthsText),
      suggestions: this.parseList(suggestionsText),
    };
  }

  private extractSection(text: string, startIndex: number, nextIndex: number): string {
    if (startIndex < 0) return '';
    const colon = text.indexOf(':', startIndex);
    const sectionStart = colon >= 0 ? colon + 1 : startIndex;
    const sectionEnd = nextIndex > startIndex ? nextIndex : text.length;
    return text.slice(sectionStart, sectionEnd).trim();
  }

  private parseList(text: string): string[] {
    if (!text) return [];
    return text
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => line.replace(/^[-*\\u2022]\\s*/, '').trim())
      .filter(Boolean);
  }

  readonly formatDate = formatDate;
  readonly formatStatusLabel = formatStatusLabel;
}
