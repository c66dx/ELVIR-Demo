import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import type { YouthWithLastSession } from '../../../core/services/api.service';
import { formatDate } from '../../../shared/utils/date-format.util';

/** Lista de jóvenes asignados al profesional. Filtros por búsqueda, estado y login. */
@Component({
  selector: 'app-jovenes-list',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './jovenes-list.component.html',
  styleUrl: './jovenes-list.component.scss',
})
export class JovenesListComponent implements OnInit {
  private api = inject(ApiService);

  youths: YouthWithLastSession[] = [];
  loading = true;
  page = 1;
  total = 0;
  readonly pageSize = 20;

  filterSearch = '';
  filterStatus: '' | 'active' | 'inactive' = '';
  filterLogin: '' | 'yes' | 'no' = '';
  private searchDebounce: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.loadYouths();
  }

  loadYouths(): void {
    this.loading = true;
    const params: { search?: string; is_active?: boolean; login_enabled?: boolean } = {};
    if (this.filterSearch.trim()) params.search = this.filterSearch.trim();
    if (this.filterStatus === 'active') params.is_active = true;
    if (this.filterStatus === 'inactive') params.is_active = false;
    if (this.filterLogin === 'yes') params.login_enabled = true;
    if (this.filterLogin === 'no') params.login_enabled = false;
    this.api.getYouthsPaged({ ...params, page: this.page, page_size: this.pageSize }).subscribe({
      next: (paged) => {
        this.youths = paged.items;
        this.total = paged.total;
        this.page = paged.page;
        this.loading = false;
      },
      error: () => (this.loading = false),
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
    this.filterStatus = '';
    this.filterLogin = '';
    this.page = 1;
    this.loadYouths();
  }

  readonly formatDate = formatDate;

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
    this.api.deactivateYouth(youth.id).subscribe({
      next: () => this.loadYouths(),
    });
  }

  onActivate(youth: YouthWithLastSession): void {
    if (!confirm(`¿Reactivar a ${youth.display_name}?`)) return;
    this.api.activateYouth(youth.id).subscribe({
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

