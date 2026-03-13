import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { catchError, forkJoin, of } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { NotificationService } from '../../../core/services/notification.service';
import { StatusBadgeComponent } from '../../../shared/status-badge/status-badge.component';
import type { Session } from '../../../core/models/session.model';
import type { Youth } from '../../../core/models/youth.model';
import type { TranscriptEntry, TranscriptResponse } from '../../../core/models/transcript.model';
import type { InterviewSummary } from '../../../core/models/interview-summary.model';
import type { SessionEvent } from '../../../core/models/session-event.model';
import type { SessionAudio } from '../../../core/models/session-audio.model';
import { durationBetween, formatDate, formatDuration } from '../../../shared/utils/date-format.util';

type SideTab = 'resumen' | 'competencias' | 'eventos';

type SessionCompetencyResponse = {
  session_id: number;
  items: {
    competency: { slug: string; name: string };
    level: { slug: string; label: string };
    comment: string | null;
  }[];
};

@Component({
  selector: 'app-session-view',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, StatusBadgeComponent],
  templateUrl: './session-view.component.html',
  styleUrl: './session-view.component.scss',
})
export class SessionViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private api = inject(ApiService);
  private fb = inject(FormBuilder);
  private notification = inject(NotificationService);

  sessionId = '';
  returnUrl = signal<string | null>(null);
  private summaryTabRequested = false;
  private editSummaryRequested = false;

  loading = signal(true);
  notFound = signal(false);

  session = signal<Session | null>(null);
  youth = signal<Youth | null>(null);
  context = signal<{ jobRoleName: string; caseName: string } | null>(null);
  transcript = signal<TranscriptResponse | null>(null);
  summary = signal<InterviewSummary | null>(null);
  events = signal<SessionEvent[]>([]);
  competencies = signal<{ competency: string; level: string; comment: string | null }[]>([]);
  audio = signal<SessionAudio | null>(null);

  sideTab = signal<SideTab>('resumen');
  showUser = signal(true);
  showAvatar = signal(true);
  editingSummary = signal(false);
  submittingSummary = signal(false);
  summaryForm!: FormGroup;

  ngOnInit(): void {
    this.sessionId = this.route.snapshot.paramMap.get('sessionId') ?? '';
    const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');
    this.returnUrl.set(returnUrl && returnUrl.startsWith('/') ? returnUrl : null);
    this.summaryTabRequested = this.route.snapshot.queryParamMap.has('summary');
    this.editSummaryRequested = this.route.snapshot.queryParamMap.has('editSummary');
    if (this.summaryTabRequested) {
      this.sideTab.set('resumen');
    }

    if (!this.sessionId) {
      this.notFound.set(true);
      this.loading.set(false);
      return;
    }

    this.summaryForm = this.fb.nonNullable.group({
      summary_text: ['', Validators.required],
      competency_tags: [''],
    });

    this.api.getSession(this.sessionId).subscribe({
      next: (session) => {
        if (!session) {
          this.notFound.set(true);
          this.loading.set(false);
          return;
        }
        this.session.set(session);
        this.loadSessionExtras(session);
      },
      error: () => {
        this.notFound.set(true);
        this.loading.set(false);
      },
    });
  }

  private loadSessionExtras(session: Session): void {
    this.api.getYouth(session.youth_id).subscribe({
      next: (y) => this.youth.set(y),
      error: () => this.youth.set(null),
    });

    forkJoin({
      context: this.api.getSessionContext(this.sessionId).pipe(catchError(() => of(null))),
      transcript: this.api.getSessionTranscript(this.sessionId).pipe(catchError(() => of(null))),
      summary: this.api.getSessionSummary(this.sessionId).pipe(catchError(() => of(null))),
      audio: this.api.getSessionAudio(this.sessionId).pipe(catchError(() => of(null))),
      events: this.api.getSessionEvents(this.sessionId).pipe(catchError(() => of([]))),
      competencies: this.api.getSessionCompetencies(this.sessionId).pipe(
        catchError(() => of({ session_id: 0, items: [] } as SessionCompetencyResponse))
      ),
    }).subscribe({
      next: ({ context, transcript, summary, audio, events, competencies }) => {
        this.context.set(context);
        this.transcript.set(transcript);
        this.summary.set(summary);
        this.audio.set(audio);
        this.applySummaryForm(summary);
        if (this.editSummaryRequested) {
          this.editingSummary.set(true);
        }
        this.events.set(events ?? []);
        const mapped = (competencies?.items ?? []).map((item) => ({
          competency: item.competency.name || item.competency.slug,
          level: item.level.label || item.level.slug,
          comment: item.comment ?? null,
        }));
        this.competencies.set(mapped);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  private applySummaryForm(summary: InterviewSummary | null): void {
    const tags = summary?.competency_tags?.length ? summary.competency_tags.join(', ') : '';
    this.summaryForm.reset({
      summary_text: summary?.summary_text ?? '',
      competency_tags: tags,
    });
  }

  setSideTab(tab: SideTab): void {
    this.sideTab.set(tab);
  }

  toggleRole(role: 'user' | 'avatar', event: Event): void {
    const target = event.target as HTMLInputElement | null;
    const checked = target?.checked ?? true;
    if (role === 'user') {
      this.showUser.set(checked);
    } else {
      this.showAvatar.set(checked);
    }
  }

  filteredTranscript(): TranscriptEntry[] {
    const data = this.transcript()?.transcript_data ?? [];
    return data.filter((entry) => {
      if (entry.role === 'user') return this.showUser();
      if (entry.role === 'avatar') return this.showAvatar();
      return true;
    });
  }

  formatRelativeTime(seconds?: number): string {
    if (seconds == null) return '';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  getDuration(session: Session): string {
    if (session.duration_seconds) return formatDuration(session.duration_seconds);
    if (session.started_at && session.ended_at) {
      return formatDuration(durationBetween(session.started_at, session.ended_at));
    }
    return '-';
  }

  eventLabel(eventType: string): string {
    const labels: Record<string, string> = {
      CREATED: 'Sesión creada',
      LIVEAVATAR_STARTED: 'LiveAvatar iniciado',
      LIVEAVATAR_FALLBACK: 'Fallback LiveAvatar',
      ENDED: 'Sesión finalizada',
    };
    return labels[eventType] ?? eventType;
  }

  eventDetail(event: SessionEvent): string | null {
    const payload = event.payload ?? {};
    const fields = [
      payload.status ? `Estado: ${payload.status}` : null,
      payload.reason ? `Motivo: ${payload.reason}` : null,
      payload.motivo ? `Detalle: ${payload.motivo}` : null,
      payload.detail ? String(payload.detail) : null,
    ].filter(Boolean);
    return fields.length ? fields.join(' · ') : null;
  }

  startEditSummary(): void {
    this.editingSummary.set(true);
    this.applySummaryForm(this.summary());
  }

  cancelEditSummary(): void {
    this.editingSummary.set(false);
    this.applySummaryForm(this.summary());
  }

  submitSummary(): void {
    if (this.summaryForm.invalid || this.submittingSummary()) return;
    const value = this.summaryForm.getRawValue();
    const tags = value.competency_tags
      ? value.competency_tags.split(',').map((t: string) => t.trim()).filter(Boolean)
      : undefined;
    this.submittingSummary.set(true);
    this.api.createSessionSummary(this.sessionId, { summary_text: value.summary_text, competency_tags: tags }).subscribe({
      next: (summary) => {
        if (summary) {
          this.summary.set(summary);
          this.applySummaryForm(summary);
          this.editingSummary.set(false);
          this.notification.success('Resumen guardado correctamente.');
        }
        this.submittingSummary.set(false);
      },
      error: () => {
        this.notification.error('No se pudo guardar el resumen.');
        this.submittingSummary.set(false);
      },
    });
  }

  initials(name?: string | null): string {
    if (!name) return 'J';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return 'J';
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

  readonly formatDate = formatDate;
  readonly formatDuration = formatDuration;
}
