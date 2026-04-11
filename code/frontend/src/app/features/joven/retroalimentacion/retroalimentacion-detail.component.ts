import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError, map, startWith, switchMap } from 'rxjs/operators';
import { SessionApiService } from '@core/services/session-api.service';
import { formatDate, formatStatusLabel } from '@shared/utils/date-format.util';
import { parseSummary } from './retroalimentacion.utils'; 
 interface FeedbackDetail { 
 sessionId: string; 
 startedAt: string; 
 status: string; 
 jobRoleName?: string; 
 caseName?: string; 
 summaryText?: string; 
 strengths: string[]; 
 suggestions: string[]; 
 hasSummary: boolean;
} 
 type FeedbackVm =   | { state: 'loading' } 
 | { state: 'notfound' } 
 | { state: 'ready'; detail: FeedbackDetail }; 
 @Component({ 
 selector: 'app-retroalimentacion-detail-joven',   standalone: true,   imports: [CommonModule, RouterLink],   templateUrl: './retroalimentacion-detail.component.html',   styleUrl: './retroalimentacion-detail.component.scss',
})
export class RetroalimentacionDetailJovenComponent { 
 private sessionsApi = inject(SessionApiService); 
 private route = inject(ActivatedRoute); 
 vm$ = this.route.paramMap.pipe(   map((params) => params.get('sessionId')  ?? ''),   switchMap((sessionId) => { 
 if (!sessionId) return of<FeedbackVm>({ state: 'notfound' as const }); 
 return forkJoin({ 
 session: this.sessionsApi.getSession(sessionId).pipe(catchError(() => of(null))),   context: this.sessionsApi.getSessionContext(sessionId).pipe(catchError(() => of(null))),   summary: this.sessionsApi.getSessionSummary(sessionId).pipe(catchError(() => of(null))),   }).pipe(   map(({ session, context, summary }) => { 
 if (!session) return { state: 'notfound' as const } as FeedbackVm; 
 const parsed = parseSummary(summary?.summary_text); 
 const hasSummary = Boolean(parsed.general || parsed.strengths.length || parsed.suggestions.length); 
 const detail: FeedbackDetail = { 
 sessionId,   startedAt: session.started_at || '',   status: session.status,   jobRoleName: context?.jobRoleName,   caseName: context?.caseName,   summaryText: parsed.general,   strengths: parsed.strengths,   suggestions: parsed.suggestions,   hasSummary,   }; 
 return { state: 'ready' as const, detail }; 
 }),   catchError(() => of<FeedbackVm>({ state: 'notfound' as const }))   ); 
 }),   startWith<FeedbackVm>({ state: 'loading' as const })   ); 
 readonly formatDate = formatDate; 
 readonly formatStatusLabel = formatStatusLabel;
}


