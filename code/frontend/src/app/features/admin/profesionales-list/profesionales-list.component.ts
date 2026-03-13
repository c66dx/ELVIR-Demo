import { Component, inject, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';

/** Lista de profesionales (Admin). */
@Component({
  selector: 'app-profesionales-list',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './profesionales-list.component.html',
  styleUrl: './profesionales-list.component.scss',
})
export class ProfesionalesListComponent implements OnInit {
  private api = inject(ApiService);

  professionals: { id: string; display_name: string; specialty?: string; institution?: string; is_active: boolean }[] = [];
  loading = true;
  page = 1;
  total = 0;
  readonly pageSize = 20;

  ngOnInit(): void {
    this.loadPage(1);
  }

  loadPage(page: number): void {
    this.loading = true;
    this.api.getProfessionalsPaged({ page, page_size: this.pageSize }).subscribe({
      next: (list) => {
        this.professionals = list.items;
        this.total = list.total;
        this.page = list.page;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  totalPages(): number {
    return Math.max(1, Math.ceil(this.total / this.pageSize));
  }

  prevPage(): void {
    if (this.page > 1) {
      this.loadPage(this.page - 1);
    }
  }

  nextPage(): void {
    if (this.page < this.totalPages()) {
      this.loadPage(this.page + 1);
    }
  }
}
