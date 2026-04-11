import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  DestroyRef,
  inject,
  OnDestroy,
  OnInit,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Subject, switchMap, Observable } from 'rxjs';
import { SessionsFacade, type SessionRow, type YouthOption } from '@features/profesional/sesiones/sessions.facade';
import type { PagedResult } from '@core/services/api-types';
import { StatusBadgeComponent } from '@shared/status-badge/status-badge.component';
import { formatDate, formatDuration } from '@shared/utils/date-format.util';
import { UploadUrlPipe } from '@core/pipes/upload-url.pipe';

@Component({
  selector: 'app-sessions-list',
  standalone: true,
  imports: [RouterLink, StatusBadgeComponent, FormsModule, UploadUrlPipe],
  templateUrl: './sessions-list.component.html',
  styleUrl: './sessions-list.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SessionsListComponent implements OnInit, OnDestroy {
  private facade = inject(SessionsFacade);
  private cdr = inject(ChangeDetectorRef);
  private destroyRef = inject(DestroyRef);

  private readonly sessionsLoad$ = new Subject<void>();

  sessions: SessionRow[] = [];
  loading = true;
  page = 1;
  total = 0;
  readonly pageSize = 20;
  errorMessage = '';
  youthOptions: YouthOption[] = [];
  filterYouthId = '';
  filterStatus: '' | 'EN_CURSO' | 'COMPLETADA' | 'CANCELADA' | 'ERROR' = '';
  filterMode: '' | 'AUTOGESTIONADA' | 'SUPERVISADA' = '';
  filterSearch = '';
  filterStartDate = '';
  filterEndDate = '';
  private searchDebounce: ReturnType<typeof setTimeout> | null = null;

  readonly statusOptions: { value: 'EN_CURSO' | 'COMPLETADA' | 'CANCELADA' | 'ERROR'; label: string }[] = [
    { value: 'EN_CURSO', label: 'En curso' },
    { value: 'COMPLETADA', label: 'Completada' },
    { value: 'CANCELADA', label: 'Cancelada' },
    { value: 'ERROR', label: 'Error' },
  ];
  readonly modeOptions: { value: 'AUTOGESTIONADA' | 'SUPERVISADA'; label: string }[] = [
    { value: 'AUTOGESTIONADA', label: 'Autogestionada' },
    { value: 'SUPERVISADA', label: 'Supervisada' },
  ];

  ngOnInit(): void {
    this.facade
      .getYouthOptions()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (youths) => {
          this.youthOptions = youths;
          this.cdr.markForCheck();
        },
      });

    this.sessionsLoad$
      .pipe(
        switchMap(() => this.fetchSessions$()),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (paged) => {
          this.sessions = paged.items;
          this.total = paged.total;
          this.page = paged.page;
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: (err: unknown) => {
          const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
          const msg = detail ?? 'No se pudieron cargar las entrevistas.';
          this.errorMessage = typeof msg === 'string' ? msg : 'No se pudieron cargar las entrevistas.';
          this.sessions = [];
          this.total = 0;
          this.loading = false;
          this.cdr.markForCheck();
        },
      });

    this.loadSessions();
  }

  ngOnDestroy(): void {
    if (this.searchDebounce) {
      clearTimeout(this.searchDebounce);
    }
  }

  /** Carga sesiones; si llega otra petición antes de terminar, la anterior se cancela (switchMap). */
  loadSessions(): void {
    if (this.isDateRangeInvalid()) {
      this.errorMessage = 'Rango de fechas inválido: "Desde" no puede ser mayor que "Hasta".';
      this.loading = false;
      this.cdr.markForCheck();
      return;
    }
    this.sessionsLoad$.next();
  }

  private fetchSessions$(): Observable<PagedResult<SessionRow>> {
    this.errorMessage = '';
    this.loading = true;
    this.cdr.markForCheck();

    return this.facade.getSessionsPage({
      page: this.page,
      pageSize: this.pageSize,
      youthId: this.filterYouthId || undefined,
      search: this.filterSearch || undefined,
      status: this.filterStatus || undefined,
      mode: this.filterMode || undefined,
      startDate: this.filterStartDate || undefined,
      endDate: this.filterEndDate || undefined,
    });
  }

  totalPages(): number {
    return Math.max(1, Math.ceil(this.total / this.pageSize));
  }

  prevPage(): void {
    if (this.page > 1) {
      this.page -= 1;
      this.loadSessions();
    }
  }

  nextPage(): void {
    if (this.page < this.totalPages()) {
      this.page += 1;
      this.loadSessions();
    }
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

  onFilterChange(): void {
    this.page = 1;
    this.loadSessions();
  }

  onSearchInput(): void {
    if (this.searchDebounce) clearTimeout(this.searchDebounce);
    this.searchDebounce = setTimeout(() => {
      this.page = 1;
      this.loadSessions();
    }, 300);
  }

  clearFilters(): void {
    this.filterYouthId = '';
    this.filterStatus = '';
    this.filterMode = '';
    this.filterSearch = '';
    this.filterStartDate = '';
    this.filterEndDate = '';
    this.errorMessage = '';
    this.page = 1;
    this.loadSessions();
  }

  private isDateRangeInvalid(): boolean {
    if (!this.filterStartDate || !this.filterEndDate) return false;
    return this.filterStartDate > this.filterEndDate;
  }
}


