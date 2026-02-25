import { Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { Observable, of } from 'rxjs';
import { switchMap, map } from 'rxjs/operators';
import { forkJoin } from 'rxjs';
import { YouthService } from '../../../core/services/youth.service';
import { StatusBadgeComponent } from '../../../shared/status-badge/status-badge.component';
import { ApiService } from '../../../core/services/api.service';
import type { Session } from '../../../core/models/session.model';
import type { JobRole } from '../../../core/models/job-role.model';
import type { Case } from '../../../core/models/case.model';
import type { SimulationTemplate } from '../../../core/models/simulation-template.model';

interface SessionWithLabel extends Session {
  templateLabel?: string;
}

@Component({
  selector: 'app-historial-joven',
  standalone: true,
  imports: [AsyncPipe, StatusBadgeComponent],
  templateUrl: './historial-joven.component.html',
  styleUrl: './historial-joven.component.scss',
})
export class HistorialJovenComponent {
  private youthService = inject(YouthService);
  private api = inject(ApiService);

  formatDate(iso?: string): string {
    if (!iso) return '-';
    return new Date(iso).toLocaleDateString('es-CL', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  formatDuration(seconds?: number): string {
    if (!seconds) return '-';
    if (seconds < 60) return `${seconds} s`;
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return s > 0 ? `${m} min ${s} s` : `${m} min`;
  }

  sessions$: Observable<SessionWithLabel[]> = this.youthService.getCurrentYouthId().pipe(
    switchMap((youthId) =>
      youthId
        ? this.api.getSessions({ youth_id: youthId }).pipe(
            switchMap((sessions) =>
              forkJoin({
                jobRoles: this.api.getJobRoles(),
                cases: this.api.getCases(),
                templates: this.api.getSimulationTemplates(),
              }).pipe(
                map(({ jobRoles, cases, templates }) => {
                  const jobMap = new Map(jobRoles.map((j) => [j.id, j]));
                  const caseMap = new Map(cases.map((c) => [c.id, c]));
                  return sessions.map((s) => {
                    const t = templates.find((tpl) => tpl.id === s.simulation_template_id);
                    const jobName = t ? jobMap.get(t.job_role_id)?.name : '';
                    const caseName = t ? caseMap.get(t.case_id)?.name : '';
                    return {
                      ...s,
                      templateLabel: jobName && caseName ? `${jobName} / ${caseName}` : '-',
                    };
                  });
                })
              )
            )
          )
        : of([])
    )
  );
}
