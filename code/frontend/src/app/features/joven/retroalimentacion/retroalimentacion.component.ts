import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { BehaviorSubject, combineLatest, forkJoin, Observable, of } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';
import { YouthService } from '../../../core/services/youth.service';
import { ApiService } from '../../../core/services/api.service';
import type { Session } from '../../../core/models/session.model';
import type { InterviewSummary } from '../../../core/models/interview-summary.model';
import { formatDate, formatStatusLabel } from '../../../shared/utils/date-format.util';
import { parseSummary } from './retroalimentacion.utils'; 
 interface FeedbackItem { 
 sessionId: string; 
 startedAt: string; 
 status: string; 
 jobRoleName?: string; 
 caseName?: string; 
 summaryText?: string; 
 strengths: string[]; 
 suggestions: string[];
} 
 interface FeedbackPage { 
 items: FeedbackItem[]; 
 total: number; 
 page: number; 
 page_size: number;
} 
 @Component({ 
 selector: 'app-retroalimentacion-joven',   standalone: true,   imports: [CommonModule, RouterLink],   templateUrl: './retroalimentacion.component.html',   styleUrl: './retroalimentacion.component.scss',
})
export class RetroalimentacionJovenComponent { 
 private youthService = inject(YouthService); 
 private api = inject(ApiService); 
 private pageSubject = new BehaviorSubject(1); 
 readonly pageSize = 10; 
 feedback$: Observable<FeedbackPage> = combineLatest([this.youthService.getCurrentYouthId(), this.pageSubject]).pipe(   switchMap(([youthId, page]) => { 
 if (!youthId) { 
 return of({ items: [], total: 0, page, page_size: this.pageSize } as FeedbackPage); 
 } 
 return this.api.getSessionsPaged({ youth_id: youthId, page, page_size: this.pageSize }).pipe(   switchMap((paged) =>   this.buildFeedbackItems(paged.items).pipe(   map((items) => ({ 
 items,   total: paged.total,   page: paged.page,   page_size: paged.page_size,   }))   )   ),   catchError(() => of({ items: [], total: 0, page, page_size: this.pageSize } as FeedbackPage))   ); 
 }),   catchError(() => of({ items: [], total: 0, page: 1, page_size: this.pageSize } as FeedbackPage))   ); 
 private buildFeedbackItems(sessions: Session[]) { 
 if (sessions.length === 0) return of([] as FeedbackItem[]); 
 const items$ = sessions.map((session) =>   forkJoin({ 
 context: this.api.getSessionContext(session.id).pipe(catchError(() => of(null))),   summary: this.api.getSessionSummary(session.id).pipe(catchError(() => of(null))),   }).pipe(map(({ context, summary }) => this.mapFeedbackItem(session, summary, context?.jobRoleName, context?.caseName)))   ); 
 return forkJoin(items$).pipe(   map((items) =>   items.sort((a, b) => { 
 if (!a.startedAt || !b.startedAt) return 0; 
 return b.startedAt.localeCompare(a.startedAt); 
 })   )   ); 
 } 
 private mapFeedbackItem(   session: Session,   summary: InterviewSummary | null,   jobRoleName?: string,   caseName?: string   ): FeedbackItem { 
 const parsed = parseSummary(summary?.summary_text); 
 return { 
 sessionId: session.id,   startedAt: session.started_at || '',   status: session.status,   jobRoleName,   caseName,   summaryText: parsed.general,   strengths: parsed.strengths,   suggestions: parsed.suggestions,   }; 
 } 
 readonly formatDate = formatDate; 
 readonly formatStatusLabel = formatStatusLabel; 
 totalPages(total: number): number { 
 if (!total) return 1; 
 return Math.max(1, Math.ceil(total / this.pageSize)); 
 } 
 prevPage(): void { 
 const current = this.pageSubject.getValue(); 
 if (current <= 1) return; 
 this.pageSubject.next(current - 1); 
 } 
 nextPage(total: number): void { 
 const current = this.pageSubject.getValue(); 
 const max = this.totalPages(total); 
 if (current >= max) return; 
 this.pageSubject.next(current + 1); 
 }
}
