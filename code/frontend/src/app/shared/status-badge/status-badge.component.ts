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
      padding: 0.2rem 0.65rem;
      font-size: 0.72rem;
      font-weight: 700;
      border-radius: 999px;
      letter-spacing: 0.02em;
    }
    .status-badge--EN_CURSO { background: var(--color-info-light); color: var(--color-info); }
    .status-badge--COMPLETADA { background: var(--color-success-light); color: var(--color-success); }
    .status-badge--CANCELADA { background: var(--color-warning-light); color: var(--color-warning); }
    .status-badge--ERROR { background: var(--color-danger-light); color: var(--color-danger); }
  `],
})
export class StatusBadgeComponent {
  status = input<SessionStatus | string | null | undefined>(null);
  label = computed(() => {
    const s = this.status();
    return s ? (STATUS_LABELS[s] ?? s) : '-';
  });
}
