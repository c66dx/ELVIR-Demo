import { CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import { 
 SessionEndService,   type SessionEndData,
} from '../../../../core/services/session-end.service';
import type { SessionStatus } from '../../../../core/models/types.model';
import { formatDuration } from '../../../../shared/utils/date-format.util'; 
 type SessionSummary = NonNullable<SessionEndData['sessionSummary']>; 
 /** Pantalla post-simulación: muestra estado (COMPLETADA/CANCELADA/ERROR), resumen y enlaces. */
@Component({ 
 selector: 'app-session-end',   standalone: true,   imports: [CommonModule, RouterLink],   templateUrl: './session-end.component.html',   styleUrl: './session-end.component.scss',
})
export class SessionEndComponent implements OnInit { 
 private router = inject(Router); 
 private auth = inject(AuthService); 
 sessionEndService = inject(SessionEndService); 
 status: SessionStatus | null = null; 
 motivo: string | null = null; 
 youthId: string | null = null; 
 sessionSummary: SessionSummary | null = null; 
 isJoven = false; 
 isProfesional = false; 
 ngOnInit(): void { 
 const data = this.sessionEndService.get(); 
 this.status = data?.status  ?? null; 
 this.motivo = data?.motivo  ?? null; 
 this.youthId = data?.youthId  ?? null; 
 this.sessionSummary = data?.sessionSummary  ?? null; 
 const role = this.auth.getRole(); 
 this.isJoven = role === 'JOVEN'; 
 this.isProfesional = role === 'PROFESIONAL'; 
 if (!this.status) { 
 this.router.navigateByUrl(this.isProfesional ? '/profesional/dashboard' : '/joven/simulacion/nueva'); 
 } 
 } 
 get title(): string { 
 switch (this.status) { 
 case 'COMPLETADA':   return 'Entrevista completada'; 
 case 'CANCELADA':   return 'Entrevista cancelada'; 
 case 'ERROR':   return 'Entrevista finalizada con error'; 
 default:   return 'Entrevista finalizada'; 
 } 
 } 
 get statusLabel(): string { 
 switch (this.status) { 
 case 'COMPLETADA':   return 'Completada'; 
 case 'CANCELADA':   return 'Cancelada'; 
 case 'ERROR':   return 'Con error'; 
 default:   return 'Finalizada'; 
 } 
 } 
 get heroTitle(): string { 
 switch (this.status) { 
 case 'COMPLETADA':   return '¡Entrevista completada!'; 
 case 'CANCELADA':   return 'Entrevista pausada'; 
 case 'ERROR':   return 'Tuvimos un problema técnico'; 
 default:   return 'Entrevista finalizada'; 
 } 
 } 
 get heroSubtitle(): string { 
 switch (this.status) { 
 case 'COMPLETADA':   return 'Buen trabajo. Tu esfuerzo queda registrado y es parte de tu progreso.'; 
 case 'CANCELADA':   return 'No pasa nada. Puedes retomarla cuando estés listo/a.'; 
 case 'ERROR':   return 'Tu avance quedó guardado. Te recomendamos reintentar cuando estés listo/a.'; 
 default:   return 'Gracias por participar en la simulación.'; 
 } 
 } 
 get feedbackMessage(): string { 
 if (this.status === 'COMPLETADA' && this.isJoven) { 
 return 'Recibirás retroalimentación de tu tutor. Mientras tanto, revisa material sugerido para seguir mejorando.'; 
 } 
 if (this.status === 'COMPLETADA' && this.isProfesional) { 
 return 'Puedes registrar un resumen y dejar retroalimentación para el joven.'; 
 } 
 if (this.status === 'CANCELADA') { 
    return 'Cuando quieras, vuelve a intentarlo para completar tu práctica.';
 } 
 if (this.status === 'ERROR') { 
 return 'Si el problema persiste, intenta nuevamente o contacta al equipo de soporte.'; 
 } 
 return ''; 
 } 
 get variant(): 'success' | 'warning' | 'error' { 
 switch (this.status) { 
 case 'COMPLETADA':   return 'success'; 
 case 'CANCELADA':   return 'warning'; 
 case 'ERROR':   return 'error'; 
 default:   return 'warning'; 
 } 
 } 
 onVolver(): void { 
 const data = this.sessionEndService.get(); 
 const returnUrl = data?.returnUrl; 
 const target = returnUrl ?? (this.isProfesional ? '/profesional/dashboard' : '/joven/simulacion/nueva'); 
 this.sessionEndService.clear(); 
 this.router.navigateByUrl(target); 
 } 
 readonly formatDuration = formatDuration;
}


