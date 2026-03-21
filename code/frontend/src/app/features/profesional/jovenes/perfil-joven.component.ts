import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { forkJoin } from 'rxjs';
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

type ProfileTab = 'perfil' | 'accesos' | 'desempeno' | 'sesiones';

interface ChartSeries {
  name: string;
  data: number[];
}

interface ChartDefinition {
  id: string;
  title: string;
  description?: string;
  unit?: string;
  x: string[];
  series: ChartSeries[];
}

const MOCK_CHARTS: ChartDefinition[] = [
  {
    id: 'comunicacion',
    title: 'Comunicación',
    description: 'Claridad y estructura al expresar ideas durante la entrevista.',
    unit: '%',
    x: ['Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul'],
    series: [{ name: 'Puntaje', data: [48, 55, 61, 66, 70, 74] }],
  },
  {
    id: 'empatia',
    title: 'Empatía',
    description: 'Capacidad de conectar con el entrevistador en contextos sensibles.',
    unit: '%',
    x: ['Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul'],
    series: [{ name: 'Puntaje', data: [38, 46, 52, 58, 63, 68] }],
  },
  {
    id: 'autogestion',
    title: 'Autogestión',
    description: 'Manejo emocional y organización durante la entrevista.',
    unit: '%',
    x: ['Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul'],
    series: [
      { name: 'Autogestionada', data: [42, 50, 57, 60, 66, 71] },
      { name: 'Supervisada', data: [35, 44, 49, 55, 59, 64] },
    ],
  },
];

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
  activeTab = signal<ProfileTab>('perfil');
  sessionsPage = signal(1);
  sessionsTotal = signal(0);
  readonly sessionsPageSize = 10;
  platformPage = signal(1);
  platformTotal = signal(0);
  readonly platformPageSize = 10;
  photoUploading = signal(false);
  photoError = signal<string | null>(null);
  sessionStats = signal<{
    total: number;
    completed: number;
    cancelled: number;
    error: number;
    in_progress: number;
    monthly: { month: string; count: number }[];
  } | null>(null);

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

    this.route.queryParamMap.subscribe((params) => {
      const tab = params.get('tab');
      if (tab === 'perfil' || tab === 'accesos' || tab === 'desempeno' || tab === 'sesiones') {
        this.activeTab.set(tab);
      }
    });

    forkJoin({
      youth: this.api.getYouth(this.youthId),
      competencies: this.api.getCompetencies(),
      competencyLevels: this.api.getCompetencyLevels(),
      stats: this.api.getSessionStats({ youth_id: this.youthId, months: 6 }),
    }).subscribe({
      next: ({ youth, competencies, competencyLevels, stats }) => {
        this.youth.set(youth);
        this.photoError.set(null);
        this.competencies.set(competencies);
        this.competencyLevels.set(competencyLevels);
        this.applyStats(stats);
        this.loadSessionsPage();
        this.loadPlatformPage();
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
    this.setTab('sesiones');
    this.showSuggestMaterialPanel.set(true);
    this.suggestMaterialForm.reset({ material_id: '', reason: '', session_id: '' });
    this.api.getSupportMaterial().subscribe({
      next: (materials) => this.supportMaterials.set(materials),
    });
    // Scroll a la sección después de que Angular la renderice
    setTimeout(() => this.scrollToSuggestMaterial(), 100);
  }

  initials(name?: string | null): string {
    if (!name) return 'J';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return 'J';
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

  onPhotoSelected(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file || !this.youthId) return;
    this.photoError.set(null);
    this.photoUploading.set(true);
    this.api.uploadYouthPhoto(this.youthId, file).subscribe({
      next: (res) => {
        this.photoUploading.set(false);
        if ('error' in res) {
          this.photoError.set(res.error);
          return;
        }
        this.youth.set(res);
        this.notification.success('Foto actualizada correctamente');
      },
      error: (err) => {
        const msg = err?.error?.detail ?? 'Error al subir foto';
        this.photoUploading.set(false);
        this.photoError.set(typeof msg === 'string' ? msg : 'Error al subir foto');
      },
    });
    if (input) input.value = '';
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
    this.loadSummariesForSessions(this.sessions());
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

  charts = signal<ChartDefinition[]>(MOCK_CHARTS);
  /** Métricas de desempeño: total, completadas, tasa */
  metricsSummary = signal<{ total: number; completed: number; cancelled: number; error: number; completionRate: number } | null>(null);
  readonly checklistItems = PROFILE_CHECKLIST_ITEMS;

  getChecklistLabels(youth: Youth): string[] {
    const slugs = youth.profile_checklist ?? [];
    return slugs
      .map((s) => this.checklistItems.find((i) => i.slug === s)?.label)
      .filter((l): l is string => !!l);
  }

  private applyStats(stats: {
    total: number;
    completed: number;
    cancelled: number;
    error: number;
    in_progress: number;
    monthly: { month: string; count: number }[];
  }): void {
    this.sessionStats.set(stats);
    this.metricsSummary.set(this.buildMetricsSummaryFromStats(stats));
  }

  private loadSessionsPage(): void {
    this.api.getSessionsWithTemplateLabelPaged({
      youth_id: this.youthId,
      page: this.sessionsPage(),
      page_size: this.sessionsPageSize,
    }).subscribe({
      next: (paged) => {
        this.sessions.set(paged.items);
        this.sessionsTotal.set(paged.total);
        this.loadSummariesForSessions(paged.items);
      },
    });
  }

  private loadPlatformPage(): void {
    this.api.getPlatformSessionsPaged(this.youthId, {
      page: this.platformPage(),
      page_size: this.platformPageSize,
    }).subscribe({
      next: (paged) => {
        this.platformSessions.set(paged.items);
        this.platformTotal.set(paged.total);
      },
    });
  }

  private loadSummariesForSessions(sessions: SessionWithTemplateLabel[]): void {
    if (sessions.length === 0) {
      this.summariesBySession.set(new Map());
      return;
    }
    forkJoin(sessions.map((s) => this.api.getSessionSummary(s.id))).subscribe({
      next: (summaries) => {
        const map = new Map<string, InterviewSummary>();
        summaries.forEach((s) => {
          if (s) map.set(s.session_id, s);
        });
        this.summariesBySession.set(map);
      },
    });
  }

  getSeriesPath(chart: ChartDefinition, series: ChartSeries): string {
    if (!series.data.length) return '';
    const max = this.getChartMax(chart);
    const points = series.data.map((value, i) => {
      const x = series.data.length === 1 ? 50 : (i / (series.data.length - 1)) * 100;
      const y = 100 - (value / max) * 100;
      return { x, y };
    });
    return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  }

  getSeriesColor(index: number): string {
    const palette = ['#1b7f79', '#4f6ef7', '#f59e0b', '#ec4899'];
    return palette[index % palette.length];
  }

  private getChartMax(chart: ChartDefinition): number {
    const values = chart.series.flatMap((s) => s.data);
    return Math.max(1, ...values);
  }

  private buildMetricsSummaryFromStats(stats: {
    total: number;
    completed: number;
    cancelled: number;
    error: number;
  }): { total: number; completed: number; cancelled: number; error: number; completionRate: number } {
    const total = stats.total || 0;
    const completed = stats.completed || 0;
    const cancelled = stats.cancelled || 0;
    const error = stats.error || 0;
    const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;
    return { total, completed, cancelled, error, completionRate };
  }

  totalPages(total: number, pageSize: number): number {
    return Math.max(1, Math.ceil(total / pageSize));
  }

  setTab(tab: ProfileTab): void {
    this.activeTab.set(tab);
  }

  prevSessionsPage(): void {
    const current = this.sessionsPage();
    if (current > 1) {
      this.sessionsPage.set(current - 1);
      this.loadSessionsPage();
    }
  }

  nextSessionsPage(): void {
    const current = this.sessionsPage();
    if (current < this.totalPages(this.sessionsTotal(), this.sessionsPageSize)) {
      this.sessionsPage.set(current + 1);
      this.loadSessionsPage();
    }
  }

  prevPlatformPage(): void {
    const current = this.platformPage();
    if (current > 1) {
      this.platformPage.set(current - 1);
      this.loadPlatformPage();
    }
  }

  nextPlatformPage(): void {
    const current = this.platformPage();
    if (current < this.totalPages(this.platformTotal(), this.platformPageSize)) {
      this.platformPage.set(current + 1);
      this.loadPlatformPage();
    }
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
    this.setTab('sesiones');
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

