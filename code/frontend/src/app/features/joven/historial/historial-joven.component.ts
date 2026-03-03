import { Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Observable, of } from 'rxjs';
import { switchMap, map } from 'rxjs/operators';
import { YouthService } from '../../../core/services/youth.service';
import { StatusBadgeComponent } from '../../../shared/status-badge/status-badge.component';
import { ApiService, type SessionWithTemplateLabel } from '../../../core/services/api.service';
import type { InterviewSummary } from '../../../core/models/interview-summary.model';
import { formatDate, formatDuration } from '../../../shared/utils/date-format.util';

interface SessionWithLabel extends SessionWithTemplateLabel {
  summary?: InterviewSummary;
}

@Component({
  selector: 'app-historial-joven',
  standalone: true,
  imports: [AsyncPipe, RouterLink, StatusBadgeComponent],
  templateUrl: './historial-joven.component.html',
  styleUrl: './historial-joven.component.scss',
})
export class HistorialJovenComponent {
  private youthService = inject(YouthService);
  private api = inject(ApiService);

  readonly formatDate = formatDate;
  readonly formatDuration = formatDuration;

  sessions$: Observable<SessionWithLabel[]> = this.youthService.getCurrentYouthId().pipe(
    switchMap((youthId) =>
      youthId
        ? this.api.getSessionsWithTemplateLabel({ youth_id: youthId }).pipe(
            switchMap((sessions) =>
              this.api.getSummariesByYouth(youthId).pipe(
                map((summaries) => {
                  const summaryMap = new Map(summaries.map((sum) => [sum.session_id, sum]));
                  return sessions.map((s) => ({ ...s, summary: summaryMap.get(s.id) }));
                })
              )
            )
          )
        : of([])
    )
  );
}
