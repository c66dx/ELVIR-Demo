import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, type AuditLogRow } from '../../../core/services/api.service';
import { formatDate } from '../../../shared/utils/date-format.util';

@Component({
  selector: 'app-audit-logs',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './audit-logs.component.html',
  styleUrl: './audit-logs.component.scss',
})
export class AuditLogsComponent implements OnInit {
  private api = inject(ApiService);

  logs: AuditLogRow[] = [];
  loading = true;
  page = 1;
  total = 0;
  readonly pageSize = 25;

  filterSearch = '';
  filterAction = '';
  filterEntity = '';
  filterStatus = '';
  filterMethod = '';
  private searchDebounce: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.loadLogs();
  }

  loadLogs(): void {
    this.loading = true;
    const params: {
      page: number;
      page_size: number;
      search?: string;
      action?: string;
      entity_type?: string;
      status_code?: number;
      method?: string;
    } = { page: this.page, page_size: this.pageSize };

    if (this.filterSearch.trim()) params.search = this.filterSearch.trim();
    if (this.filterAction) params.action = this.filterAction;
    if (this.filterEntity) params.entity_type = this.filterEntity;
    if (this.filterMethod) params.method = this.filterMethod;
    const statusValue = Number(this.filterStatus);
    if (this.filterStatus && !Number.isNaN(statusValue)) params.status_code = statusValue;

    this.api.getAuditLogs(params).subscribe({
      next: (res) => {
        this.logs = res.items;
        this.total = res.total;
        this.page = res.page;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  onFilterChange(): void {
    this.page = 1;
    this.loadLogs();
  }

  onSearchInput(): void {
    if (this.searchDebounce) clearTimeout(this.searchDebounce);
    this.searchDebounce = setTimeout(() => {
      this.page = 1;
      this.loadLogs();
    }, 350);
  }

  clearFilters(): void {
    this.filterSearch = '';
    this.filterAction = '';
    this.filterEntity = '';
    this.filterStatus = '';
    this.filterMethod = '';
    this.page = 1;
    this.loadLogs();
  }

  totalPages(): number {
    return Math.max(1, Math.ceil(this.total / this.pageSize));
  }

  prevPage(): void {
    if (this.page > 1) {
      this.page -= 1;
      this.loadLogs();
    }
  }

  nextPage(): void {
    if (this.page < this.totalPages()) {
      this.page += 1;
      this.loadLogs();
    }
  }

  actionLabel(action: string): string {
    switch (action) {
      case 'create':
        return 'Crear';
      case 'update':
        return 'Actualizar';
      case 'delete':
        return 'Eliminar';
      case 'login':
        return 'Login';
      case 'logout':
        return 'Logout';
      case 'activate':
        return 'Activar';
      default:
        return action || '-';
    }
  }

  entityLabel(entity?: string): string {
    switch (entity) {
      case 'youth':
        return 'Joven';
      case 'professional':
        return 'Profesional';
      case 'session':
        return 'Sesión';
      case 'assignment':
        return 'Asignación';
      case 'material':
        return 'Material';
      case 'summary':
        return 'Resumen';
      case 'auth':
        return 'Auth';
      case 'upload':
        return 'Subida';
      default:
        return entity || '-';
    }
  }

  readonly formatDate = formatDate;
}
