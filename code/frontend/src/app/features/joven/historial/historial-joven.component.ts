import { Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Observable, of, BehaviorSubject, combineLatest, forkJoin } from 'rxjs';
import { switchMap, map } from 'rxjs/operators';
import { YouthService } from '../../../core/services/youth.service';
import { StatusBadgeComponent } from '../../../shared/status-badge/status-badge.component';
import { ApiService, type SessionWithTemplateLabel } from '../../../core/services/api.service';
import type { InterviewSummary } from '../../../core/models/interview-summary.model';
import { formatDate, formatDuration } from '../../../shared/utils/date-format.util'; 
 interface SessionWithLabel extends SessionWithTemplateLabel { 
 summary?: InterviewSummary;
} 
 interface SessionPage { 
 items: SessionWithLabel[]; 
 total: number; 
 page: number; 
 page_size: number;
} 
 @Component({ 
 selector: 'app-historial-joven',   standalone: true,   imports: [AsyncPipe, RouterLink, StatusBadgeComponent],   templateUrl: './historial-joven.component.html',   styleUrl: './historial-joven.component.scss',
})
export class HistorialJovenComponent { 
 private youthService = inject(YouthService); 
 private api = inject(ApiService); 
 private page$ = new BehaviorSubject(1); 
 readonly pageSize = 10; 
 readonly formatDate = formatDate; 
 readonly formatDuration = formatDuration; 
 data$: Observable<SessionPage> = combineLatest([this.youthService.getCurrentYouthId(), this.page$]).pipe(   switchMap(([youthId, page]) =>   youthId   ? this.api.getSessionsWithTemplateLabelPaged({ youth_id: youthId, page, page_size: this.pageSize }).pipe(   switchMap((paged) => { 
 if (paged.items.length === 0) { 
 return of({ ...paged, items: [] }); 
 } 
 return forkJoin(paged.items.map((s) => this.api.getSessionSummary(s.id))).pipe(   map((summaries) => { 
 const summaryMap = new Map<string, InterviewSummary>(); 
 summaries.forEach((sum) => { 
 if (sum) summaryMap.set(sum.session_id, sum); 
 }); 
 return { 
 ...paged,   items: paged.items.map((s) => ({ ...s, summary: summaryMap.get(s.id) })),   }; 
 })   ); 
 })   )   : of({ items: [], total: 0, page: 1, page_size: this.pageSize })   )   ); 
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
}
