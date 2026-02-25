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

  ngOnInit(): void {
    this.api.getProfessionals().subscribe({
      next: (list) => {
        this.professionals = list;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }
}
