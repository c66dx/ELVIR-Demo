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
import type { SupportMaterial } from '../../../core/models/support-material.model';
import type { InterviewSummary } from '../../../core/models/interview-summary.model';
import type { TranscriptResponse } from '../../../core/models/transcript.model';
import { formatDate, formatDuration, durationBetween } from '../../../shared/utils/date-format.util';
import type { SessionWithTemplateLabel, PlatformSessionItem } from '../../../core/services/api.service';

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
  sessions = signal<SessionWithTemplateLabel[]>([]);
  platformSessions = signal<PlatformSessionItem[]>([]);
  summariesBySession = signal<Map<string, InterviewSummary>>(new Map());
  loading = signal(true);

  showSummaryForm = signal(false);
  selectedSessionId = signal<string | null>(null);
  sessionTranscript = signal<TranscriptResponse | null>(null);
  loadingTranscript = signal(false);
  summaryForm!: FormGroup;
  submittingSummary = signal(false);

  competencies = signal<{ id: string; slug: string; name: string; is_active: boolean }[]>([]);
  competencyLevels = signal<{ id: string; slug: string; label: string; sort_order: number }[]>([]);
  sessionCompetencies = signal<{ competency_slug: string; level_slug: string | null }[]>([]);
  loadingSessionCompetencies = signal(false);

  showSuggestMaterialPanel = signal(false);
  supportMaterials = signal<SupportMaterial[]>([]);
  suggestMaterialForm!: FormGroup;
  submittingSuggest = signal(false);

  ngOnInit(): void {
    this.youthId = this.route.snapshot.paramMap.get('youthId') ?? '';
    if (!this.youthId) return;

    forkJoin({
      youth: this.api.getYouth(this.youthId),
      sessions: this.api.getSessionsWithTemplateLabel({ youth_id: this.youthId }),
      summaries: this.api.getSummariesByYouth(this.youthId),
      platformSessions: this.api.getPlatformSessions(this.youthId),
      competencies: this.api.getCompetencies(),
      competencyLevels: this.api.getCompetencyLevels(),
    })
      .pipe(
        map(({ youth, sessions: sessionsWithLabel, summaries, platformSessions, competencies, competencyLevels }) => {
          const summariesMap = new Map<string, InterviewSummary>();
          summaries.forEach((sum) => summariesMap.set(sum.session_id, sum));
          return { youth, sessionsWithLabel, summariesMap, platformSessions, competencies, competencyLevels };
        })
      )
      .subscribe({
        next: ({ youth, sessionsWithLabel, summariesMap, platformSessions, competencies, competencyLevels }) => {
          this.youth.set(youth);
          this.sessions.set(sessionsWithLabel);
          this.summariesBySession.set(summariesMap);
          this.platformSessions.set(platformSessions);
          this.competencies.set(competencies);
          this.competencyLevels.set(competencyLevels);
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

  private scrollToSummaryForm(): void {
    const el = document.getElementById('registrar-resumen');
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

  private buildChartData(sessions: SessionWithTemplateLabel[]): { month: string; count: number; maxCount: number }[] {
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

  private buildMetricsSummary(sessions: SessionWithTemplateLabel[]): { total: number; completed: number; cancelled: number; error: number; completionRate: number } | null {
    const total = sessions.length;
    if (total === 0) return { total: 0, completed: 0, cancelled: 0, error: 0, completionRate: 0 };
    const completed = sessions.filter((s) => s.status === 'COMPLETADA').length;
    const cancelled = sessions.filter((s) => s.status === 'CANCELADA').length;
    const error = sessions.filter((s) => s.status === 'ERROR').length;
    const completionRate = Math.round((completed / total) * 100);
    return { total, completed, cancelled, error, completionRate };
  }

  readonly formatDate = formatDate;
  readonly formatDuration = formatDuration;
  readonly durationBetween = durationBetween;

  getCompetencyName(slug: string): string {
    const list = this.competencies();
    const found = list.find((c) => c.slug === slug);
    return found?.name ?? slug;
  }

  openSummaryForm(sessionId: string): void {
    this.selectedSessionId.set(sessionId);
    this.showSummaryForm.set(true);
    this.sessionTranscript.set(null);
    const existing = this.summariesBySession().get(sessionId);
    this.summaryForm.reset({
      summary_text: existing?.summary_text ?? '',
      competency_tags: existing?.competency_tags?.join(', ') ?? '',
    });
    this.loadingTranscript.set(true);
    this.api.getSessionTranscript(sessionId).subscribe({
      next: (t) => {
        this.sessionTranscript.set(t);
        this.loadingTranscript.set(false);
      },
      error: () => this.loadingTranscript.set(false),
    });
    this.loadSessionCompetencies(sessionId);
    setTimeout(() => this.scrollToSummaryForm(), 100);
  }

  private loadSessionCompetencies(sessionId: string): void {
    const comps = this.competencies();
    if (comps.length === 0) {
      this.sessionCompetencies.set([]);
      return;
    }
    this.loadingSessionCompetencies.set(true);
    this.api.getSessionCompetencies(sessionId).subscribe({
      next: (res) => {
        const levelBySlug = new Map<string, string>();
        res.items.forEach((item) => {
          levelBySlug.set(item.competency.slug, item.level.slug);
        });
        const rows = comps.map((c) => ({
          competency_slug: c.slug,
          level_slug: levelBySlug.get(c.slug) ?? null,
        }));
        this.sessionCompetencies.set(rows);
        this.loadingSessionCompetencies.set(false);
      },
      error: () => {
        this.sessionCompetencies.set([]);
        this.loadingSessionCompetencies.set(false);
      },
    });
  }

  updateSessionCompetencyLevel(competencySlug: string, levelSlug: string): void {
    const current = this.sessionCompetencies();
    const updated = current.map((row) =>
      row.competency_slug === competencySlug ? { ...row, level_slug: levelSlug || null } : row
    );
    this.sessionCompetencies.set(updated);
  }

  onCompetencyLevelChange(competencySlug: string, event: Event): void {
    const target = event.target as HTMLSelectElement | null;
    const value = target?.value ?? '';
    this.updateSessionCompetencyLevel(competencySlug, value);
  }

  cancelSummaryForm(): void {
    this.showSummaryForm.set(false);
    this.selectedSessionId.set(null);
    this.sessionTranscript.set(null);
  }

  submitSummary(): void {
    if (this.summaryForm.invalid) return;

    const sessionId = this.selectedSessionId();
    if (!sessionId) return;

    const value = this.summaryForm.getRawValue();
    const tags = value.competency_tags
      ? value.competency_tags.split(',').map((t: string) => t.trim()).filter(Boolean)
      : undefined;

    const evalItems = this.sessionCompetencies()
      .filter((row) => row.level_slug)
      .map((row) => ({
        competency_slug: row.competency_slug,
        level_slug: row.level_slug as string,
        comment: undefined,
      }));

    this.submittingSummary.set(true);
    forkJoin([
      this.api.createSessionSummary(sessionId, { summary_text: value.summary_text, competency_tags: tags }),
      this.api.createSessionCompetencies(sessionId, evalItems),
    ]).subscribe({
      next: () => {
        this.submittingSummary.set(false);
        this.cancelSummaryForm();
        this.loadSummaries();
      },
      error: () => this.submittingSummary.set(false),
    });
  }
}
