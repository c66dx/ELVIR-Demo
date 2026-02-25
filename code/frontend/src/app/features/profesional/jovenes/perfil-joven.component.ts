import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { map } from 'rxjs/operators';
import { ApiService } from '../../../core/services/api.service';
import { NotificationService } from '../../../core/services/notification.service';
import { StatusBadgeComponent } from '../../../shared/status-badge/status-badge.component';
import type { Youth } from '../../../core/models/youth.model';
import { PROFILE_CHECKLIST_ITEMS } from '../../../core/models/youth.model';
import type { Session } from '../../../core/models/session.model';
import type { JobRole } from '../../../core/models/job-role.model';
import type { Case } from '../../../core/models/case.model';
import type { SimulationTemplate } from '../../../core/models/simulation-template.model';
import type { SupportMaterial } from '../../../core/models/support-material.model';
import type { InterviewSummary } from '../../../core/models/interview-summary.model';

interface SessionWithLabel extends Session {
  templateLabel?: string;
}

/**
 * Perfil del joven: datos, historial de sesiones, resúmenes, sugerir material.
 * El profesional puede registrar resúmenes cualitativos e iniciar simulación supervisada.
 */
@Component({
  selector: 'app-perfil-joven',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, StatusBadgeComponent],
  templateUrl: './perfil-joven.component.html',
  styleUrl: './perfil-joven.component.scss',
})
export class PerfilJovenComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private api = inject(ApiService);
  private fb = inject(FormBuilder);
  private notification = inject(NotificationService);

  youthId = '';
  youth = signal<Youth | null>(null);
  sessions = signal<SessionWithLabel[]>([]);
  summariesBySession = signal<Map<string, InterviewSummary>>(new Map());
  loading = signal(true);

  showSummaryForm = signal(false);
  selectedSessionId = signal<string | null>(null);
  summaryForm!: FormGroup;
  submittingSummary = signal(false);

  showSuggestMaterialPanel = signal(false);
  supportMaterials = signal<SupportMaterial[]>([]);
  suggestMaterialForm!: FormGroup;
  submittingSuggest = signal(false);

  ngOnInit(): void {
    this.youthId = this.route.snapshot.paramMap.get('youthId') ?? '';
    if (!this.youthId) return;

    forkJoin({
      youth: this.api.getYouth(this.youthId),
      sessions: this.api.getSessions({ youth_id: this.youthId }),
      summaries: this.api.getSummariesByYouth(this.youthId),
      jobRoles: this.api.getJobRoles(),
      cases: this.api.getCases(),
      templates: this.api.getSimulationTemplates(),
    })
      .pipe(
        map(({ youth, sessions, summaries, jobRoles, cases, templates }) => {
          const jobMap = new Map<string, JobRole>(jobRoles.map((j) => [j.id, j]));
          const caseMap = new Map<string, Case>(cases.map((c) => [c.id, c]));
          const sessionsWithLabel: SessionWithLabel[] = sessions.map((s) => {
            const t = templates.find((tpl) => tpl.id === s.simulation_template_id);
            const jobName = t ? jobMap.get(t.job_role_id)?.name : '';
            const caseName = t ? caseMap.get(t.case_id)?.name : '';
            return {
              ...s,
              templateLabel: jobName && caseName ? `${jobName} / ${caseName}` : '-',
            };
          });
          const summariesMap = new Map<string, InterviewSummary>();
          summaries.forEach((sum) => summariesMap.set(sum.session_id, sum));
          return { youth, sessionsWithLabel, summariesMap };
        })
      )
      .subscribe({
        next: ({ youth, sessionsWithLabel, summariesMap }) => {
          this.youth.set(youth);
          this.sessions.set(sessionsWithLabel);
          this.summariesBySession.set(summariesMap);
          const chart = this.buildChartData(sessionsWithLabel);
          this.chartData.set(chart);
          this.chartLinePoints.set(this.buildLinePoints(chart));
          this.metricsSummary.set(this.buildMetricsSummary(sessionsWithLabel));
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });

    this.summaryForm = this.fb.nonNullable.group({
      summary_text: ['', Validators.required],
      competency_tags: [''],
    });

    this.suggestMaterialForm = this.fb.nonNullable.group({
      material_id: ['', Validators.required],
      reason: [''],
      session_id: [''],
    });
  }

  openSuggestMaterialPanel(): void {
    this.showSuggestMaterialPanel.set(true);
    this.suggestMaterialForm.reset({ material_id: '', reason: '', session_id: '' });
    this.api.getSupportMaterial().subscribe({
      next: (materials) => this.supportMaterials.set(materials),
    });
    // Scroll a la sección después de que Angular la renderice
    setTimeout(() => this.scrollToSuggestMaterial(), 100);
  }

  private scrollToSuggestMaterial(): void {
    const el = document.getElementById('sugerir-material');
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  cancelSuggestMaterial(): void {
    this.showSuggestMaterialPanel.set(false);
  }

  loadSummaries(): void {
    if (!this.youthId) return;
    this.api.getSummariesByYouth(this.youthId).subscribe({
      next: (summaries) => {
        const map = new Map<string, InterviewSummary>();
        summaries.forEach((s) => map.set(s.session_id, s));
        this.summariesBySession.set(map);
      },
    });
  }

  submitSuggestMaterial(): void {
    if (this.suggestMaterialForm.invalid) return;

    const value = this.suggestMaterialForm.getRawValue();
    this.submittingSuggest.set(true);
    this.api
      .suggestMaterial({
        youth_id: this.youthId,
        material_id: value.material_id,
        reason: value.reason || undefined,
        session_id: value.session_id || undefined,
      })
      .subscribe({
        next: () => {
          this.submittingSuggest.set(false);
          this.notification.success('Material sugerido correctamente. El joven lo verá en "Sugerido para ti".');
          this.cancelSuggestMaterial();
        },
        error: () => this.submittingSuggest.set(false),
      });
  }

  chartData = signal<{ month: string; count: number; maxCount: number }[]>([]);
  /** Puntos para la curva SVG: { x, y } en coordenadas 0-100 */
  chartLinePoints = signal<{ x: number; y: number }[]>([]);
  /** Métricas de desempeño: total, completadas, tasa */
  metricsSummary = signal<{ total: number; completed: number; cancelled: number; error: number; completionRate: number } | null>(null);
  readonly checklistItems = PROFILE_CHECKLIST_ITEMS;

  getChecklistLabels(youth: Youth): string[] {
    const slugs = youth.profile_checklist ?? [];
    return slugs
      .map((s) => this.checklistItems.find((i) => i.slug === s)?.label)
      .filter((l): l is string => !!l);
  }

  private buildChartData(sessions: SessionWithLabel[]): { month: string; count: number; maxCount: number }[] {
    const completed = sessions.filter((s) => s.status === 'COMPLETADA' && s.ended_at);
    const byMonth = new Map<string, number>();
    const now = new Date();
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      byMonth.set(key, 0);
    }
    completed.forEach((s) => {
      if (!s.ended_at) return;
      const d = new Date(s.ended_at);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      if (byMonth.has(key)) byMonth.set(key, (byMonth.get(key) ?? 0) + 1);
    });
    const labels: Record<string, string> = {
      '01': 'Ene', '02': 'Feb', '03': 'Mar', '04': 'Abr', '05': 'May', '06': 'Jun',
      '07': 'Jul', '08': 'Ago', '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dic',
    };
    const rows = Array.from(byMonth.entries()).map(([key, count]) => {
      const [, month] = key.split('-');
      return { month: labels[month] ?? month, count };
    });
    const maxCount = Math.max(1, ...rows.map((r) => r.count));
    return rows.map((r) => ({ ...r, maxCount }));
  }

  private buildLinePoints(chart: { count: number; maxCount: number }[]): { x: number; y: number }[] {
    if (chart.length === 0) return [];
    const maxCount = Math.max(1, ...chart.map((r) => r.count));
    return chart.map((item, i) => {
      const x = (i / (chart.length - 1 || 1)) * 100;
      const y = 100 - (item.count / maxCount) * 100;
      return { x, y };
    });
  }

  getLinePath(): string {
    const points = this.chartLinePoints();
    if (points.length === 0) return '';
    return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  }

  private buildMetricsSummary(sessions: SessionWithLabel[]): { total: number; completed: number; cancelled: number; error: number; completionRate: number } | null {
    const total = sessions.length;
    if (total === 0) return { total: 0, completed: 0, cancelled: 0, error: 0, completionRate: 0 };
    const completed = sessions.filter((s) => s.status === 'COMPLETADA').length;
    const cancelled = sessions.filter((s) => s.status === 'CANCELADA').length;
    const error = sessions.filter((s) => s.status === 'ERROR').length;
    const completionRate = Math.round((completed / total) * 100);
    return { total, completed, cancelled, error, completionRate };
  }

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

  openSummaryForm(sessionId: string): void {
    this.selectedSessionId.set(sessionId);
    this.showSummaryForm.set(true);
    const existing = this.summariesBySession().get(sessionId);
    this.summaryForm.reset({
      summary_text: existing?.summary_text ?? '',
      competency_tags: existing?.competency_tags?.join(', ') ?? '',
    });
  }

  cancelSummaryForm(): void {
    this.showSummaryForm.set(false);
    this.selectedSessionId.set(null);
  }

  submitSummary(): void {
    if (this.summaryForm.invalid) return;

    const sessionId = this.selectedSessionId();
    if (!sessionId) return;

    const value = this.summaryForm.getRawValue();
    const tags = value.competency_tags
      ? value.competency_tags.split(',').map((t: string) => t.trim()).filter(Boolean)
      : undefined;

    this.submittingSummary.set(true);
    this.api.createSessionSummary(sessionId, { summary_text: value.summary_text, competency_tags: tags }).subscribe({
      next: () => {
        this.submittingSummary.set(false);
        this.cancelSummaryForm();
        this.loadSummaries();
      },
      error: () => this.submittingSummary.set(false),
    });
  }
}
