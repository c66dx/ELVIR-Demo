import { Component, input, computed } from '@angular/core';
import type { SessionStatus } from '../../core/models/types.model';

const STATUS_LABELS: Record<string, string> = {
  EN_CURSO: 'En curso',
  COMPLETADA: 'Completada',
  CANCELADA: 'Cancelada',
  ERROR: 'Error',
};

@Component({
  selector: 'app-status-badge',
  standalone: true,
  template: `@if (status(); as s) {<span class="status-badge status-badge--{{ s }}">{{ label() }}</span>} @else {<span>-</span>}`,
  styles: [`
    .status-badge {
      display: inline-block;
      padding: 0.25rem 0.6rem;
      font-size: 0.75rem;
      font-weight: 600;
      border-radius: 6px;
    }
    .status-badge--EN_CURSO { background: #e8f4fd; color: #0d6efd; }
    .status-badge--COMPLETADA { background: #e8f5ef; color: #2f8f6b; }
    .status-badge--CANCELADA { background: #fef9ed; color: #d19a38; }
    .status-badge--ERROR { background: #fce8e6; color: #c44d3c; }
  `],
})
export class StatusBadgeComponent {
  status = input<SessionStatus | string | null | undefined>(null);
  label = computed(() => {
    const s = this.status();
    return s ? (STATUS_LABELS[s] ?? s) : '-';
  });
}
