import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe, NgClass } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Observable, of, BehaviorSubject, combineLatest } from 'rxjs';
import { switchMap, map } from 'rxjs/operators';
import { YouthService } from '@core/services/youth.service';
import { StatusBadgeComponent } from '@shared/status-badge/status-badge.component';
import type { SessionWithTemplateLabel } from '@core/services/api-types';
import type { InterviewSummary } from '@core/models/interview-summary.model';
import { formatDate, formatDuration } from '@shared/utils/date-format.util'; 
import { HistorialJovenFacade } from '@features/joven/historial/historial-joven.facade';
 interface SessionWithLabel extends SessionWithTemplateLabel { 
 summary?: InterviewSummary;
} 
 interface SessionPage { 
 items: SessionWithLabel[]; 
 total: number; 
 page: number; 
 page_size: number;
 groups: SessionGroup[];
}

/** Agrupa sesiones por proximidad temporal para dar ritmo sin repetir el mismo bloque visual. */
export interface SessionGroup {
  label: string;
  items: SessionWithLabel[];
}

function relativeGroupKey(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startD = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diffDays = Math.round((startToday.getTime() - startD.getTime()) / 86400000);
  if (diffDays === 0) return 'Hoy';
  if (diffDays === 1) return 'Ayer';
  if (diffDays >= 2 && diffDays < 7) return 'Esta semana';
  if (diffDays >= 7 && diffDays < 14) return 'Semana pasada';
  const my = d.toLocaleDateString('es-CL', { month: 'long', year: 'numeric' });
  return my.charAt(0).toUpperCase() + my.slice(1);
}

/** Ordena por fecha reciente y agrupa; se calcula en el flujo de datos, no en la plantilla. */
function groupSessionsByRelativeDate(items: SessionWithLabel[]): SessionGroup[] {
  const sorted = [...items].sort(
    (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
  );
  const order: string[] = [];
  const byLabel = new Map<string, SessionWithLabel[]>();
  for (const s of sorted) {
    const key = relativeGroupKey(s.started_at);
    if (!byLabel.has(key)) {
      byLabel.set(key, []);
      order.push(key);
    }
    byLabel.get(key)!.push(s);
  }
  return order.map((label) => ({ label, items: byLabel.get(label)! }));
}

@Component({ 
 selector: 'app-historial-joven',   standalone: true,   imports: [AsyncPipe, NgClass, RouterLink, StatusBadgeComponent],   templateUrl: './historial-joven.component.html',   styleUrl: './historial-joven.component.scss',
 changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HistorialJovenComponent { 
 private youthService = inject(YouthService); 
 private facade = inject(HistorialJovenFacade); 
 private page$ = new BehaviorSubject(1); 
 readonly pageSize = 10; 
 readonly formatDate = formatDate; 
 readonly formatDuration = formatDuration; 
 /** Lista paginada + resúmenes: `switchMap` cancela la petición anterior si cambia joven o página antes de que termine. */
 data$: Observable<SessionPage> = combineLatest([this.youthService.getCurrentYouthId(), this.page$]).pipe(   switchMap(([youthId, page]) =>   youthId   ? this.facade.getSessionsPage(youthId, page, this.pageSize).pipe(   switchMap((paged) => { 
 if (paged.items.length === 0) { 
 return of({ ...paged, items: [], groups: [] }); 
 } 
 return this.facade.getSessionSummariesMap(paged.items).pipe(   map((summaryMap) => { 
 const items = paged.items.map((s) => ({ ...s, summary: summaryMap.get(s.id) }));
 return { 
 ...paged,   items,   groups: groupSessionsByRelativeDate(items),   }; 
 })   ); 
 })   )   : of({ items: [], total: 0, page: 1, page_size: this.pageSize, groups: [] })   )   ); 
 totalPages(total: number): number { 
 return Math.max(1, Math.ceil(total / this.pageSize)); 
 } 
 prevPage(): void { 
 const current = this.page$.value; 
 if (current > 1) this.page$.next(current - 1); 
 } 
 nextPage(total: number): void { 
 const current = this.page$.value; 
 if (current < this.totalPages(total)) this.page$.next(current + 1); 
 }

  /** Texto cercano para el modo; el seguimiento administrativo sigue en vistas de tutor/admin. */
  modeLabel(mode: string | undefined): string {
    const m = (mode || '').toUpperCase();
    if (m === 'AUTOGESTIONADA') return 'Práctica a tu ritmo';
    if (m === 'SUPERVISADA') return 'Con acompañamiento';
    return mode || '—';
  }

  /** Una línea opcional si hay resumen del tutor (sin volver administrativo). */
  summaryTeaser(s: SessionWithLabel): string | null {
    const t = s.summary?.summary_text?.trim();
    if (!t) return null;
    return t.length > 80 ? `${t.slice(0, 77)}…` : t;
  }

  timelineDotClass(status: string | undefined): string {
    const s = (status || '').toUpperCase();
    if (s === 'COMPLETADA') return 'timeline-dot--done';
    if (s === 'EN_CURSO') return 'timeline-dot--live';
    if (s === 'CANCELADA') return 'timeline-dot--skip';
    if (s === 'ERROR') return 'timeline-dot--warn';
    return 'timeline-dot--neutral';
  }
}


