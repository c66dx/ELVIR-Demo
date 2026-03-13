import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { switchMap, map, of } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import type { SessionWithTemplateLabel } from '../../../core/services/api.service';
import { StatusBadgeComponent } from '../../../shared/status-badge/status-badge.component';
import { formatDate, formatDuration } from '../../../shared/utils/date-format.util';

type SessionRow = SessionWithTemplateLabel & {
  youthName: string;
  youthRut?: string;
  youthPhotoUrl?: string;
};

@Component({
  selector: 'app-sessions-list',
  standalone: true,
  imports: [RouterLink, StatusBadgeComponent, FormsModule],
  templateUrl: './sessions-list.component.html',
  styleUrl: './sessions-list.component.scss',
})
export class SessionsListComponent implements OnInit {
  private api = inject(ApiService);

  sessions: SessionRow[] = [];
  loading = true;
  page = 1;
  total = 0;
  readonly pageSize = 20;
  errorMessage = '';

  youthOptions: { id: string; display_name: string; rut?: string }[] = [];
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
    this.loadYouthOptions();
    this.loadSessions();
  }

  loadYouthOptions(): void {
    this.api.getYouths().subscribe({
      next: (youths) => {
        this.youthOptions = youths.map((y) => ({
          id: y.id,
          display_name: y.display_name,
          rut: y.rut,
        }));
      },
    });
  }

  loadSessions(): void {
    if (this.isDateRangeInvalid()) {
      this.errorMessage = 'Rango de fechas inválido: "Desde" no puede ser mayor que "Hasta".';
      this.loading = false;
      return;
    }
    this.errorMessage = '';
    this.loading = true;
    this.api
      .getSessionsWithTemplateLabelPaged({
        page: this.page,
        page_size: this.pageSize,
        youth_id: this.filterYouthId || undefined,
        search: this.filterSearch || undefined,
        status: this.filterStatus || undefined,
        mode: this.filterMode || undefined,
        start_date: this.filterStartDate || undefined,
        end_date: this.filterEndDate || undefined,
      })
      .pipe(
        switchMap((paged) => {
          const ids = Array.from(new Set(paged.items.map((s) => s.youth_id)));
          if (ids.length === 0) {
            return of({ paged, lookup: [] as { id: string; display_name: string; rut?: string; profile_photo_url?: string }[] });
          }
          return this.api.getYouthLookup(ids).pipe(map((lookup) => ({ paged, lookup })));
        })
      )
      .subscribe({
        next: ({ paged, lookup }) => {
          const youthMap = new Map(lookup.map((y) => [y.id, y]));
          this.sessions = paged.items.map((s) => ({
            ...s,
            youthName: youthMap.get(s.youth_id)?.display_name ?? 'Desconocido',
            youthRut: youthMap.get(s.youth_id)?.rut,
            youthPhotoUrl: youthMap.get(s.youth_id)?.profile_photo_url,
          }));
          this.total = paged.total;
          this.page = paged.page;
          this.loading = false;
        },
        error: (err) => {
          const msg = err?.error?.detail ?? 'No se pudieron cargar las sesiones.';
          this.errorMessage = typeof msg === 'string' ? msg : 'No se pudieron cargar las sesiones.';
          this.sessions = [];
          this.total = 0;
          this.loading = false;
        },
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
