import { Component, inject, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import type { YouthWithLastSession } from '../../../core/services/api.service';

/** Lista de jóvenes asignados al profesional. Permite desactivar y navegar al perfil. */
@Component({
  selector: 'app-jovenes-list',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './jovenes-list.component.html',
  styleUrl: './jovenes-list.component.scss',
})
export class JovenesListComponent implements OnInit {
  private api = inject(ApiService);

  youths: YouthWithLastSession[] = [];
  loading = true;

  ngOnInit(): void {
    this.api.getYouths().subscribe({
      next: (y) => {
        this.youths = y;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  formatDate(iso?: string): string {
    if (!iso) return '-';
    const d = new Date(iso);
    return d.toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  onDeactivate(youth: YouthWithLastSession): void {
    if (!confirm(`¿Desactivar a ${youth.display_name}?`)) return;
    this.api.deactivateYouth(youth.id).subscribe({
      next: () => {
        this.api.getYouths().subscribe((y) => (this.youths = y));
      },
    });
  }

  onActivate(youth: YouthWithLastSession): void {
    if (!confirm(`¿Reactivar a ${youth.display_name}?`)) return;
    this.api.activateYouth(youth.id).subscribe({
      next: () => {
        this.api.getYouths().subscribe((y) => (this.youths = y));
      },
    });
  }
}
