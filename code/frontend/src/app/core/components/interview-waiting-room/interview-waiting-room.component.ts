import { CommonModule } from '@angular/common';
import { Component, inject, OnDestroy, OnInit, signal, ChangeDetectionStrategy } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { SessionApiService } from '@core/services/session-api.service'; 
 interface WaitingState {
 companyName?: string; 
 companyDescription?: string; 
 jobRoleName?: string; 
 caseName?: string; 
 returnUrl?: string;
 companySector?: string;
 interviewMode?: string;
 interviewerName?: string;
 contextSummary?: string;
 motivationMessage?: string;
} 
 @Component({ 
 selector: 'app-interview-waiting-room',   standalone: true, changeDetection: ChangeDetectionStrategy.OnPush,   imports: [CommonModule],   templateUrl: './interview-waiting-room.component.html',   styleUrl: './interview-waiting-room.component.scss',
})
export class InterviewWaitingRoomComponent implements OnInit, OnDestroy { 
 private route = inject(ActivatedRoute); 
 private router = inject(Router); 
 private sessionsApi = inject(SessionApiService); 
 sessionId = ''; 
 companyName = signal('Empresa colaboradora'); 
 companyDescription = signal(''); 
 companySector = signal('Servicios empresariales'); 
 jobRoleName = signal('Entrevista laboral'); 
 caseName = signal(''); 
 interviewMode = signal('Videollamada en línea'); 
 interviewerName = signal('Javiera (IA)'); 
 contextSummary = signal('Estás a punto de iniciar una entrevista simulada enfocada en habilidades laborales reales.'); 
 motivationMessage = signal('Respira profundo: tienes las herramientas para dar una gran entrevista.'); 
 waitMs = signal(7000); 
 secondsLeft = signal(7); 
 messageIndex = signal(0); 
 messagePulse = signal(true); 
 loadingMessages = [   'La entrevistadora está ingresando a la sala',   'Revisando antecedentes del cargo',   'Verificando audio y video',   'La entrevista comenzará en unos segundos',   ]; 
 private intervalId?: number; 
 private timeoutId?: number; 
 private messageIntervalId?: number; 
 ngOnInit(): void { 
 this.sessionId = this.route.snapshot.paramMap.get('sessionId')  ?? ''; 
 this.applyStateData(); 
 if (this.sessionId) { 
 this.loadContextFromApi(); 
 } 
 this.startCountdown(); 
 this.startMessageRotation(); 
 } 
 ngOnDestroy(): void { 
 if (this.intervalId) window.clearInterval(this.intervalId); 
 if (this.timeoutId) window.clearTimeout(this.timeoutId); 
 if (this.messageIntervalId) window.clearInterval(this.messageIntervalId); 
 } 
 private applyStateData(): void { 
 const state = history.state as WaitingState | undefined; 
 if (state?.companyName) this.companyName.set(state.companyName); 
 if (state?.companyDescription) this.companyDescription.set(state.companyDescription); 
 if (state?.jobRoleName) this.jobRoleName.set(state.jobRoleName); 
 if (state?.caseName) this.caseName.set(state.caseName); 
 if (state?.companySector) this.companySector.set(state.companySector); 
 if (state?.interviewMode) this.interviewMode.set(state.interviewMode); 
 if (state?.interviewerName) this.interviewerName.set(state.interviewerName); 
 if (state?.contextSummary) this.contextSummary.set(state.contextSummary); 
 if (state?.motivationMessage) this.motivationMessage.set(state.motivationMessage); 
 if (!this.contextSummary() && state?.companyDescription) { 
 this.contextSummary.set(this.buildContextSummary(state.companyDescription, state.jobRoleName, state.caseName)); 
 } 
 } 
 private loadContextFromApi(): void { 
 this.sessionsApi.getSessionContext(this.sessionId).subscribe({ 
 next: (ctx) => { 
 if (!ctx) return; 
 if (ctx.jobRoleName) this.jobRoleName.set(ctx.jobRoleName); 
 if (ctx.caseName) this.caseName.set(ctx.caseName); 
 if (!this.companyName() || this.companyName() === 'Empresa colaboradora') { 
 const company = this.mapCompany(ctx.jobRoleName); 
 this.companyName.set(company.name); 
 this.companySector.set(company.sector); 
 } 
 if (!this.contextSummary()) { 
 this.contextSummary.set(this.buildContextSummary(this.companyDescription(), ctx.jobRoleName, ctx.caseName)); 
 } 
 },   }); 
 } 
 private startCountdown(): void { 
 const min = 5; 
 const max = 10; 
 const seconds = Math.floor(Math.random() * (max - min + 1)) + min; 
 const duration = seconds * 1000; 
 this.waitMs.set(duration); 
 this.secondsLeft.set(seconds); 
 const start = Date.now(); 
 this.intervalId = window.setInterval(() => { 
 const elapsed = Date.now() - start; 
 const remaining = Math.max(0, Math.ceil((duration - elapsed) / 1000)); 
 this.secondsLeft.set(remaining); 
 }, 250); 
 this.timeoutId = window.setTimeout(() => this.goToSimulation(), duration); 
 } 
 private startMessageRotation(): void { 
 const intervalMs = 1600; 
 this.messageIntervalId = window.setInterval(() => { 
 const next = (this.messageIndex() + 1) % this.loadingMessages.length; 
 this.messageIndex.set(next); 
 this.messagePulse.set(!this.messagePulse()); 
 }, intervalMs); 
 } 
 private goToSimulation(): void { 
 if (!this.sessionId) return; 
 const target = this.route.snapshot.data?.['target'] === 'profesional' ? '/profesional/simulacion' : '/joven/simulacion'; 
 const state = history.state?.returnUrl ? { returnUrl: history.state.returnUrl } : undefined; 
 this.router.navigate([target, this.sessionId], { state }); 
 } 
 private mapCompany(jobRoleName?: string | null): { name: string; sector: string } { 
 if (!jobRoleName) return { name: 'Empresa colaboradora', sector: 'Servicios empresariales' }; 
 const normalized = jobRoleName.toLowerCase(); 
    if (normalized.includes('operario')) return { name: 'Logística Andina', sector: 'Logística y bodegaje' };
 if (normalized.includes('atención') || normalized.includes('publico')) { 
 return { name: 'Centro Ciudadano', sector: 'Atención al cliente y servicios' }; 
 } 
    if (normalized.includes('administrativo')) return { name: 'Clínica Horizonte', sector: 'Salud y administración' };
 if (normalized.includes('técnico') || normalized.includes('tecnico')) { 
 return { name: 'TecnoSoluciones', sector: 'Servicios técnicos' }; 
 } 
 return { name: 'Empresa colaboradora', sector: 'Servicios empresariales' }; 
 } 
 private buildContextSummary(description?: string | null, role?: string | null, caseName?: string | null): string { 
 const base = description?.trim() || 'Se trata de una entrevista simulada para reforzar competencias laborales.'; 
 const roleText = role ?  `El foco está en el cargo de ${role}.` : ''; 
 const caseText = caseName ?  `El caso seleccionado es ${caseName}.` : ''; 
 return [base, roleText, caseText].filter(Boolean).join(' '); 
 }
}
