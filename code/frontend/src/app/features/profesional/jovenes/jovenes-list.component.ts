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
import { Subject, Observable } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { YouthsFacade, type YouthRow } from '@features/profesional/jovenes/youths.facade';
import type { PagedResult, YouthWithLastSession } from '@core/services/api-types';
import { formatDate, formatStatusLabel } from '@shared/utils/date-format.util';
import { UploadUrlPipe } from '@core/pipes/upload-url.pipe';


/** Lista de jóvenes asignados al profesional. Filtros por búsqueda y login. */
@Component({
  selector: 'app-jovenes-list',
  standalone: true,
  imports: [FormsModule, RouterLink, UploadUrlPipe],
  templateUrl: './jovenes-list.component.html',
  styleUrl: './jovenes-list.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class JovenesListComponent implements OnInit, OnDestroy {
  private facade = inject(YouthsFacade);
  private cdr = inject(ChangeDetectorRef);
  private destroyRef = inject(DestroyRef);

  private readonly youthsLoad$ = new Subject<void>();

  youths: YouthRow[] = [];
  loading = true;
  page = 1;
  total = 0;
  readonly pageSize = 20;
  filterSearch = '';
  filterLogin: '' | 'yes' | 'no' = '';
  private searchDebounce: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.youthsLoad$
      .pipe(
        switchMap(() => this.fetchYouths$()),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (paged) => {
          this.youths = paged.items;
          this.total = paged.total;
          this.page = paged.page;
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.loading = false;
          this.cdr.markForCheck();
        },
      });

    this.loadYouths();
  }

  ngOnDestroy(): void {
    if (this.searchDebounce) {
      clearTimeout(this.searchDebounce);
    }
  }

  /** Recarga la lista; peticiones superpuestas se cancelan (switchMap). */
  loadYouths(): void {
    this.youthsLoad$.next();
  }

  private fetchYouths$(): Observable<PagedResult<YouthRow>> {
    this.loading = true;
    this.cdr.markForCheck();

    const loginEnabled = this.filterLogin === 'yes' ? true : this.filterLogin === 'no' ? false : undefined;
    return this.facade.getYouthsPage({
      page: this.page,
      pageSize: this.pageSize,
      search: this.filterSearch,
      loginEnabled,
    });
  }

  onFilterChange(): void {
    this.page = 1;
    this.loadYouths();
  }

  onSearchInput(): void {
    if (this.searchDebounce) clearTimeout(this.searchDebounce);
    this.searchDebounce = setTimeout(() => {
      this.page = 1;
      this.loadYouths();
    }, 350);
  }

  clearFilters(): void {
    this.filterSearch = '';
    this.filterLogin = '';
    this.page = 1;
    this.loadYouths();
  }

  readonly formatDate = formatDate;
  readonly formatStatusLabel = formatStatusLabel;

  totalPages(): number {
    return Math.max(1, Math.ceil(this.total / this.pageSize));
  }

  prevPage(): void {
    if (this.page > 1) {
      this.page -= 1;
      this.loadYouths();
    }
  }

  nextPage(): void {
    if (this.page < this.totalPages()) {
      this.page += 1;
      this.loadYouths();
    }
  }

  onDeactivate(youth: YouthWithLastSession): void {
    if (!confirm(`¿Desactivar a ${youth.display_name}?`)) return;
    this.facade
      .deactivateYouth(youth.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => this.loadYouths(),
      });
  }

  onActivate(youth: YouthWithLastSession): void {
    if (!confirm(`¿Reactivar a ${youth.display_name}?`)) return;
    this.facade
      .activateYouth(youth.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => this.loadYouths(),
      });
  }

  initials(name?: string | null): string {
    if (!name) return 'J';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return 'J';
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

}


