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
    this.api.getYouths(Object.keys(params).length ? params : undefined).subscribe({
      next: (y) => {
        this.youths = y;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  onFilterChange(): void {
    this.loadYouths();
  }

  onSearchInput(): void {
    if (this.searchDebounce) clearTimeout(this.searchDebounce);
    this.searchDebounce = setTimeout(() => this.loadYouths(), 350);
  }

  clearFilters(): void {
    this.filterSearch = '';
    this.filterStatus = '';
    this.filterLogin = '';
    this.loadYouths();
  }

  readonly formatDate = formatDate;

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
}
