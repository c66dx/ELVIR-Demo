import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, OnDestroy, OnInit, signal, ViewChild, ElementRef, HostListener } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Room, RoomEvent, RemoteTrack } from 'livekit-client';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { SessionEndService } from '../../../core/services/session-end.service';
import { SimulacionRuntimeService } from './simulacion-runtime.service';
import { environment } from '../../../../environments/environment';
import type { InterviewSummary } from '../../../core/models/interview-summary.model';
import { formatDate, formatDuration, formatStatusLabel } from '../../../shared/utils/date-format.util';
import { extractErrorMessage } from '../../../core/utils/http-error.util';

/** Texto ampliado cuando el API aún devuelve el mensaje corto antiguo o no envía detalle. */
const LIVEAVATAR_EMBED_HELP =
  'LiveAvatar no está configurado: añade LIVEAVATAR_API_KEY y LIVEAVATAR_CONTEXT_ID, LIVEAVATAR_AVATAR_ID, LIVEAVATAR_VOICE_ID en code/backend/.env con valores del panel LiveAvatar (los marcadores ctx-elvir-dinamico, avatar-default y voice-default del seed no son válidos). Reinicia el servidor API tras guardar.';

function normalizeLiveavatarFallbackDetail(raw: string | undefined): string {
  const t = (raw ?? '').trim();
  if (/^liveavatar no configurado\.?$/i.test(t)) {
    return LIVEAVATAR_EMBED_HELP;
  }
  return t || LIVEAVATAR_EMBED_HELP;
}

/**   * Pantalla de simulación en curso. Muestra LiveKit (avatar video/audio) cuando está   * configurado, o iframe placeholder en caso contrario. Incluye contador, cargo/caso   * y botones para finalizar/cancelar.   */
@Component({ 
 selector: 'app-simulacion-detail',   standalone: true,   imports: [RouterLink],   templateUrl: './simulacion-detail.component.html',   styleUrl: './simulacion-detail.component.scss',
})
export class SimulacionDetailComponent implements OnInit, OnDestroy { 
 private route = inject(ActivatedRoute); 
 private api = inject(ApiService); 
 private router = inject(Router); 
 private sanitizer = inject(DomSanitizer); 
 private auth = inject(AuthService); 
 private sessionEndService = inject(SessionEndService); 
 private simulacionRuntime = inject(SimulacionRuntimeService); 
 @ViewChild('avatarVideo') avatarVideoRef?: ElementRef<HTMLVideoElement>; 
 @ViewChild('avatarAudio') avatarAudioRef?: ElementRef<HTMLAudioElement>; 
 sessionId = ''; 
 returnUrl = signal<string | null>(null); 
 youthId = signal<string | null>(null); 
 embedUrl = signal<SafeResourceUrl | null>(null); 
 useLiveKit = signal(false); 
 turnIndicator = signal('La entrevistadora está ingresando a la sala...'); 
 sessionMode = signal<string | null>(null); 
 sessionContext = signal<{ jobRoleName: string; caseName: string } | null>(null); 
 loading = signal(true); 
 error = signal<string | null>(null); 
 sessionNotFound = signal(false); 
 connectionErrorBanner = signal(false); 
 retrying = signal(false); 
 isProfessionalView = signal(false); 
 elapsedTime = signal('0:00'); 
 private room: Room | null = null; 
 private avatarIsSpeaking = false; 
 /** Verdadero si el navegador bloque el audio (politica de autoplay) y el usuario debe hacer clic. */   audioBlocked = signal(false); 
 /** Muestra una guía inicial para activar audio (solo al inicio). */   audioHintVisible = signal(false); 
 audioReady = signal(false); 
 volume = signal(0.8); 
 muted = signal(false); 
 audioPanelOpen = signal(false); 
 captionsEnabled = signal(false); 
 captionsAvailable = signal(false); 
 captionLines = signal<string[]>([]); 
 captionRole = signal<'user' | 'avatar' | 'system' | null>(null); 
 chatMessages = signal<{ id: number; text: string }[]>([]); 
 chatAvailable = signal(false); 
 audioRecording = signal<'idle' | 'recording' | 'stopped' | 'error'>('idle'); 
 audioRecordingError = signal<string | null>(null); 
 private mediaRecorder: MediaRecorder | null = null; 
 private audioChunks: Blob[] = []; 
 private audioStream: MediaStream | null = null; 
 private audioStartTime: number | null = null; 
 private audioUploaded = false; 
 private allowDeactivate = false; 
 private pendingAudioUpload: { file: File; durationSeconds?: number } | null = null; 
 private closeCompleted = false; 
 private heartbeatTimer: ReturnType<typeof setInterval> | null = null; 
/** Verdadero si la sesión ya está finalizada (COMPLETADA/CANCELADA/ERROR) -> mostrar resumen, no iniciar. */   sessionCompleted = signal(false); 
 completedSessionSummary = signal<InterviewSummary | null>(null); 
 completedSessionData = signal<{ 
 status: string; 
 started_at?: string; 
 ended_at?: string; 
 duration_seconds?: number; 
 mode?: string; 
 jobRoleName?: string; 
 caseName?: string; 
 } | null>(null); 
 ngOnInit(): void { 
 this.sessionId = this.route.snapshot.paramMap.get('sessionId')  ?? ''; 
 this.isProfessionalView.set(this.auth.getRole() === 'PROFESIONAL'); 
 const returnUrl = history.state?.['returnUrl'] as string | undefined; 
 this.returnUrl.set(returnUrl && returnUrl.startsWith('/') ? returnUrl : null); 
 if (!this.sessionId) return; 
 this.api.getSession(this.sessionId).subscribe({ 
 next: (s) => { 
 this.sessionMode.set(s.mode); 
 this.youthId.set(s.youth_id); 
 const isFinalizada = s.status === 'COMPLETADA' || s.status === 'CANCELADA' || s.status === 'ERROR'; 
 if (isFinalizada) { 
 this.sessionCompleted.set(true); 
 this.loading.set(false); 
 this.loadSessionContextForCompleted(); 
 this.completedSessionData.set({ 
 status: s.status,   started_at: s.started_at,   ended_at: s.ended_at,   duration_seconds: s.duration_seconds,   mode: s.mode,   }); 
 return; 
 } 
 this.doStartSession(); 
 },   error: (err) => { 
 this.loading.set(false); 
 if (err instanceof HttpErrorResponse && err.status === 404) { 
 this.sessionNotFound.set(true); 
 return; 
 } 
 this.connectionErrorBanner.set(true); 
 this.error.set(extractErrorMessage(err)); 
 },   }); 
 } 
 private loadSessionContextForCompleted(): void { 
 this.api.getSessionContext(this.sessionId).subscribe({ 
 next: (ctx) => { 
 if (ctx) { 
 this.completedSessionData.update((d) =>   d ?  { ...d, jobRoleName: ctx.jobRoleName, caseName: ctx.caseName } : d   ); 
 } 
 },   }); 
 if (this.isProfessionalView()) { 
 this.api.getSessionSummary(this.sessionId).subscribe({ 
 next: (summary) => summary && this.completedSessionSummary.set(summary),   }); 
 } 
 } 
 doStartSession(): void { 
 this.api.startSession(this.sessionId).subscribe({ 
 next: async (result) => { 
 this.loading.set(false); 
 this.retrying.set(false); 
 if (result) { 
 this.error.set(null); 
 this.sessionNotFound.set(false); 
 this.connectionErrorBanner.set(false); 
 this.loadSessionContext(); 
 this.startTimer(); 
 this.startHeartbeat(); 
 this.startAudioRecording(); 
 this.turnIndicator.set('Revisando antecedentes del cargo...'); 
 if (result.livekit_url && result.access_token) { 
 this.useLiveKit.set(true); 
 this.audioHintVisible.set(true); 
 this.embedUrl.set(null); 
 setTimeout(() => this.connectToLiveKit(result.livekit_url!, result.access_token!), 150); 
 } else if (result.embed?.url) {
 this.useLiveKit.set(false);
 this.audioHintVisible.set(false);
 this.embedUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(result.embed.url));
 this.connectionErrorBanner.set(true);
 this.error.set(normalizeLiveavatarFallbackDetail(result.fallback_detail));
 } else { 
 this.connectionErrorBanner.set(true); 
 this.error.set('Respuesta inválida del servidor'); 
 } 
 } else { 
 this.sessionNotFound.set(true); 
 this.error.set(null); 
 this.connectionErrorBanner.set(false); 
 } 
 },   error: (err) => { 
 this.loading.set(false); 
 this.retrying.set(false); 
 this.connectionErrorBanner.set(true); 
 this.error.set(err instanceof HttpErrorResponse ? extractErrorMessage(err) : 'Error al iniciar la entrevista'); 
 },   }); 
 } 
 private async connectToLiveKit(url: string, token: string): Promise<void> { 
 const videoEl = this.avatarVideoRef?.nativeElement; 
 const audioEl = this.avatarAudioRef?.nativeElement; 
 if (!videoEl || !audioEl) { 
 this.error.set('Elementos de video/audio no disponibles'); 
 this.connectionErrorBanner.set(true); 
 return; 
 } 
 try { 
 this.room = new Room(); 
 this.room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => { 
 if (track.kind === 'video') { 
 videoEl.srcObject = new MediaStream([track.mediaStreamTrack]); 
 } 
 if (track.kind === 'audio') { 
 if (audioEl.srcObject) return; 
 if (track.mediaStreamTrack.muted) track.mediaStreamTrack.enabled = true; 
 const stream = new MediaStream([track.mediaStreamTrack]); 
 audioEl.srcObject = stream; 
 this.audioReady.set(true); 
 this.applyAudioVolume(); 
 // Intentar autoplay; si el navegador lo bloquea, mostramos el botón de activación.   this.audioBlocked.set(true); 
 audioEl.play().then(() => { 
 this.audioBlocked.set(false); 
 this.audioHintVisible.set(false); 
 }).catch(() => { 
 this.audioBlocked.set(true); 
 }); 
 setTimeout(() => { 
 if (audioEl.paused) { 
 this.audioBlocked.set(true); 
 } 
 }, 1500); 
 } 
 }); 
 this.room.on(RoomEvent.DataReceived, (payload: Uint8Array) => { 
 try { 
 const data = JSON.parse(new TextDecoder().decode(payload)); 
 const eventType = data?.event_type; 
 if (typeof eventType !== 'string') return; 
 if (eventType.includes('transcript')) { 
 this.handleTranscriptEvent(data, eventType); 
 } 
 if (eventType === 'user.speak_started' && !this.avatarIsSpeaking) { 
 this.turnIndicator.set('Te escucho, adelante'); 
 } else if (eventType === 'user.speak_ended' && !this.avatarIsSpeaking) { 
 this.turnIndicator.set('Gracias, estoy analizando'); 
 } else if (eventType === 'user.transcription' && !this.avatarIsSpeaking) { 
 this.turnIndicator.set('Organizando tu respuesta...'); 
 } else if (eventType === 'avatar.speak_started') { 
 this.avatarIsSpeaking = true; 
 this.turnIndicator.set('Javiera está respondiendo'); 
 this.room?.localParticipant.setMicrophoneEnabled(false); 
 } else if (eventType === 'avatar.speak_ended') { 
 this.avatarIsSpeaking = false; 
 this.turnIndicator.set('Tu turno, te escucho'); 
 this.room?.localParticipant.setMicrophoneEnabled(true); 
 } 
 } catch { 
 // ignorar
 } 
 }); 
 await this.room.connect(url, token); 
 await this.room.localParticipant.setMicrophoneEnabled(true); 
 this.sendCommandToAvatar('avatar.start_listening'); 
 this.turnIndicator.set('La entrevista comenzará en unos segundos...'); 
 } catch (err: unknown) {
 let detail = "Error al conectar con LiveAvatar (revisa red, firewall y credenciales LiveAvatar).";
 if (err instanceof Error && err.message?.trim()) {
 detail = err.message.trim();
 } else if (typeof err === "string" && err.trim()) {
 detail = err.trim();
 }
 this.error.set(detail);
 this.connectionErrorBanner.set(true);
 this.useLiveKit.set(false);
 }
 }
 onActivarAudio(): void { 
 const audioEl = this.avatarAudioRef?.nativeElement; 
 if (audioEl?.srcObject) { 
 this.muted.set(false); 
 this.applyAudioVolume(); 
 audioEl.play().then(() => this.audioBlocked.set(false)).catch(() => { 
 this.audioBlocked.set(true); 
 }); 
 this.audioHintVisible.set(false); 
 } 
 } 
 onVolumeChange(event: Event): void { 
 const target = event.target as HTMLInputElement | null; 
 const value = Number(target?.value  ??  this.volume()); 
 this.volume.set(value); 
 if (value === 0) { 
 this.muted.set(true); 
 } 
 this.applyAudioVolume(); 
 } 
 toggleMute(): void { 
 this.muted.set(!this.muted()); 
 this.applyAudioVolume(); 
 } 
 toggleAudioPanel(): void { 
 this.audioPanelOpen.set(!this.audioPanelOpen()); 
 } 
 toggleCaptions(): void { 
 this.captionsEnabled.set(!this.captionsEnabled()); 
 } 
 captionRoleLabel(): string { 
 const role = this.captionRole(); 
 if (role === 'avatar') return 'Javiera'; 
 if (role === 'user') return 'Joven'; 
 return 'Entrevista'; 
 } 
 private applyAudioVolume(): void { 
 const audioEl = this.avatarAudioRef?.nativeElement; 
 if (!audioEl) return; 
 audioEl.muted = this.muted(); 
 audioEl.volume = this.volume(); 
 } 
 volumePercent(): number { 
 return Math.round(this.volume() * 100); 
 } 
 private sendCommandToAvatar(type: string, payload: Record<string, unknown> = {}): void { 
 if (!this.room) return; 
 try { 
 this.room.localParticipant.publishData(   new TextEncoder().encode(JSON.stringify({ type, payload })),   { reliable: true, topic: 'agent-control' } 
 ); 
 } catch { 
 // ignorar
 } 
 } 
 loadSessionContext(): void { 
 this.api.getSessionContext(this.sessionId).subscribe({ 
 next: (ctx) => ctx && this.sessionContext.set(ctx),   }); 
 } 
 onReintentar(): void { 
 this.retrying.set(true); 
 this.sessionNotFound.set(false); 
 this.connectionErrorBanner.set(false); 
 this.doStartSession(); 
 } 
 goToElegirCargo(): void { 
 if (this.isProfessionalView()) { 
 const youthId = this.youthId(); 
 if (youthId) { 
 this.router.navigate(['/profesional/jovenes', youthId, 'supervisada', 'nueva']); 
 return; 
 } 
 const returnUrl = this.returnUrl(); 
 if (returnUrl) { 
 this.router.navigateByUrl(returnUrl); 
 return; 
 } 
 this.router.navigate(['/profesional/jovenes']); 
 return; 
 } 
 this.router.navigate(['/joven/simulacion/nueva']); 
 } 
 onSalirConnectionError(): void { 
    if (!confirm('¿Salir sin completar la entrevista? Se registrará como error de conexión.')) return;
 this.stopAudioRecording(false); 
 this.stopHeartbeat(); 
 const youthId = this.youthId(); 
 this.api.closeSession(this.sessionId, { status: 'ERROR', motivo: 'LIVEAVATAR_CONNECTION' }).subscribe({ 
 next: () => { 
 const returnUrl = history.state?.['returnUrl'] as string | undefined; 
 this.sessionEndService.set({ 
 status: 'ERROR',   motivo: 'LIVEAVATAR_CONNECTION',   returnUrl,   youthId: youthId  ??  undefined,   }); 
 this.router.navigate(['/session-end']); 
 },   }); 
 } 
 private startTimer(): void { 
 this.simulacionRuntime.startTimer((label) => this.elapsedTime.set(label)); 
 } 
 private stopTimer(): void { 
 this.simulacionRuntime.stopTimer(); 
 } 
 private startHeartbeat(): void { 
 if (this.heartbeatTimer) return; 
 this.api.heartbeatSession(this.sessionId).subscribe(); 
 this.heartbeatTimer = setInterval(() => { 
 if (!this.isSessionActive()) return; 
 this.api.heartbeatSession(this.sessionId).subscribe(); 
 }, 15000); 
 } 
 private stopHeartbeat(): void { 
 if (!this.heartbeatTimer) return; 
 clearInterval(this.heartbeatTimer); 
 this.heartbeatTimer = null; 
 } 
 private isSessionActive(): boolean { 
 if (!this.sessionId) return false; 
 if (this.sessionCompleted() || this.sessionNotFound()) return false; 
 if (this.loading() || this.connectionErrorBanner() || this.error()) return false; 
 return true; 
 } 
 canDeactivate(): boolean { 
 if (this.allowDeactivate || !this.isSessionActive()) return true; 
    const confirmExit = confirm('Si sales ahora, se cancelará la entrevista. ¿Quieres salir?');
 if (confirmExit) { 
 this.closeSession('CANCELADA', 'ABANDONO', { skipConfirm: true }); 
 } 
 return false; 
 } 
@HostListener('window:beforeunload', ['$event'])
onBeforeUnload(event: BeforeUnloadEvent): void { 
 if (this.allowDeactivate || !this.isSessionActive()) return; 
 event.preventDefault(); 
 event.returnValue = ''; 
 } 
@HostListener('window:pagehide')
onPageHide(): void { 
 if (this.allowDeactivate || !this.isSessionActive()) return; 
 this.sendCancelOnUnload(); 
 } 
 ngOnDestroy(): void { 
 this.stopTimer(); 
 this.stopHeartbeat(); 
 this.stopAudioRecording(false); 
 if (this.room) { 
 this.room.disconnect(); 
 this.room = null; 
 } 
 } 
 readonly formatDate = formatDate; 
 readonly formatDuration = formatDuration; 
 readonly formatStatusLabel = formatStatusLabel; 
 primaryReturnLink(): string { 
 if (this.isProfessionalView()) { 
 return this.returnUrl()  ?? '/profesional/jovenes'; 
 } 
 return '/joven/simulacion/nueva'; 
 } 
 secondaryReturnLink(): string { 
 if (this.isProfessionalView()) { 
 return '/profesional/sesiones'; 
 } 
 return '/joven/historial'; 
 } 
 primaryReturnLabel(): string { 
 if (this.isProfessionalView()) { 
 return this.returnUrl() ? '← Volver a ficha' : '← Volver al listado'; 
 } 
 return 'Practicar nuevamente'; 
 } 
 secondaryReturnLabel(): string { 
 return this.isProfessionalView() ? 'Ver entrevistas' : 'Ver mis prácticas'; 
 } 
 companyContext(jobRoleName?: string | null): { name: string; sector: string } { 
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
 formatModeLabel(mode?: string | null): string { 
 if (!mode) return 'Entrevista simulada'; 
 if (mode === 'AUTOGESTIONADA') return 'Autogestionada'; 
 if (mode === 'SUPERVISADA') return 'Supervisada'; 
 return mode; 
 } 
 buildNarrative(data?: { 
 jobRoleName?: string; 
 caseName?: string; 
 mode?: string; 
 }): string { 
 if (!data) return 'Se registró una entrevista simulada en la plataforma.'; 
 const role = data.jobRoleName  ?? 'el cargo'; 
 const caseText = data.caseName ?  `en un escenario ${data.caseName.toLowerCase()}` : 'en un escenario simulado'; 
 const modeLabel = this.formatModeLabel(data.mode); 
 return `Participaste en una entrevista para el cargo de ${role} ${caseText}. La modalidad fue ${modeLabel.toLowerCase()}.`; 
 } 
 completedTitle(): string { 
 return this.isProfessionalView() ? 'La entrevista del joven finalizó' : 'Tu entrevista finalizó'; 
 } 
 completedSubtitle(): string { 
 return this.isProfessionalView()   ? 'Revisa el detalle de la entrevista o vuelve a la ficha del joven.'   : 'Revisa el detalle de la entrevista y la retroalimentación del tutor cuando esté disponible.'; 
 } 
 summaryTitle(): string { 
 return this.isProfessionalView() ? 'Resumen del tutor' : 'Retroalimentación del tutor'; 
 } 
 summaryEmptyText(): string { 
 return this.isProfessionalView()   ? 'Aún no hay retroalimentación registrada para esta entrevista.'   : 'Tu tutor aún no deja retroalimentación para esta entrevista.'; 
 } 
 closeSession(   status: 'COMPLETADA' | 'CANCELADA',   motivo?: string,   options?: { skipConfirm?: boolean } 
 ): void { 
 if (!options?.skipConfirm) { 
 if (status === 'COMPLETADA' && !confirm('¿Finalizar entrevista? Se registrará como completada.')) { 
 return; 
 } 
 if (   status === 'CANCELADA' &&   !confirm('¿Estás seguro de que quieres cancelar esta entrevista? Se registrará como cancelada.')   ) { 
 return; 
 } 
 } 
 this.closeCompleted = false; 
 this.pendingAudioUpload = null; 
 this.stopAudioRecording(status === 'COMPLETADA'); 
 const metrics = this.simulacionRuntime.buildCloseMetrics(status); 
 this.stopTimer(); 
 this.stopHeartbeat(); 
 const youthId = this.youthId(); 
 const ctx = this.sessionContext(); 
 this.api.closeSession(this.sessionId, { status, metrics, motivo }).subscribe({ 
 next: (session) => { 
 if (status === 'COMPLETADA') { 
 this.closeCompleted = true; 
 this.flushPendingAudioUpload(); 
 } 
 const returnUrl = history.state?.['returnUrl'] as string | undefined; 
 this.sessionEndService.set(   this.simulacionRuntime.buildSessionEndData({ 
 status,   motivo,   returnUrl,   youthId: youthId ?? undefined,   session,   context: ctx,   sessionId: this.sessionId,   })   ); 
 this.allowDeactivate = true; 
 this.router.navigate(['/session-end']); 
 },   }); 
 } 
 private async startAudioRecording(): Promise<void> { 
 if (this.audioRecording() === 'recording' || this.mediaRecorder) return; 
 if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') { 
 this.audioRecording.set('error'); 
 this.audioRecordingError.set('Grabación de audio no disponible en este navegador.'); 
 return; 
 } 
 try { 
 this.audioStream = await navigator.mediaDevices.getUserMedia({ audio: true }); 
 const mimeType = this.pickAudioMimeType(); 
 this.audioChunks = []; 
 this.mediaRecorder = new MediaRecorder(   this.audioStream,   mimeType ?  { mimeType } : undefined   ); 
 this.mediaRecorder.ondataavailable = (event: BlobEvent) => { 
 if (event.data && event.data.size > 0) { 
 this.audioChunks.push(event.data); 
 } 
 }; 
 this.audioStartTime = performance.now(); 
 this.mediaRecorder.start(); 
 this.audioRecording.set('recording'); 
 this.audioRecordingError.set(null); 
 } catch { 
 this.audioRecording.set('error'); 
 this.audioRecordingError.set('No se pudo iniciar la grabación de audio.'); 
 this.cleanupAudioRecorder(); 
 } 
 } 
 private stopAudioRecording(upload: boolean): void { 
 if (!this.mediaRecorder) return; 
 if (this.mediaRecorder.state === 'inactive') { 
 this.cleanupAudioRecorder(); 
 return; 
 } 
 const recorder = this.mediaRecorder; 
 recorder.onstop = () => { 
 const result = this.buildAudioFile(); 
 this.cleanupAudioRecorder(); 
 this.audioRecording.set('stopped'); 
 if (upload && result) { 
 this.pendingAudioUpload = result; 
 this.flushPendingAudioUpload(); 
 } 
 }; 
 try { 
 recorder.stop(); 
 } catch { 
 this.cleanupAudioRecorder(); 
 } 
 } 
 private buildAudioFile(): { file: File; durationSeconds?: number } | null { 
 if (!this.audioChunks.length) return null; 
 const type = this.audioChunks[0]?.type || 'audio/webm'; 
 const blob = new Blob(this.audioChunks, { type }); 
 const ext = this.extensionForMime(type); 
 const filename = `session_${this.sessionId}.${ext}`; 
 const file = new File([blob], filename, { type }); 
 const durationSeconds =   this.audioStartTime != null ?  Math.round((performance.now() - this.audioStartTime) / 1000) : undefined; 
 return { file, durationSeconds }; 
 } 
 private uploadSessionAudio(file: File, durationSeconds?: number, attempt = 0): void { 
 if (!this.sessionId || this.audioUploaded) return; 
 this.audioUploaded = true; 
 this.api.uploadSessionAudio(this.sessionId, file, durationSeconds).subscribe({ 
 next: (res) => { 
 if ('error' in res) { 
 this.audioUploaded = false; 
 if (this.shouldRetryAudioUpload(res.error) && attempt < 3) { 
 const delayMs = 800 * (attempt + 1); 
 setTimeout(() => this.uploadSessionAudio(file, durationSeconds, attempt + 1), delayMs); 
 return; 
 } 
 this.audioRecordingError.set(res.error); 
 } 
 },   error: (err) => { 
 this.audioUploaded = false; 
 if (this.shouldRetryAudioUpload(err) && attempt < 3) { 
 const delayMs = 800 * (attempt + 1); 
 setTimeout(() => this.uploadSessionAudio(file, durationSeconds, attempt + 1), delayMs); 
 return; 
 } 
 this.audioRecordingError.set('Error al subir el audio.'); 
 },   }); 
 } 
 private shouldRetryAudioUpload(err: unknown): boolean { 
 const detail =   typeof err === 'string'   ? err   : (err as { error?: { detail?: unknown } })?.error?.detail; 
 if (typeof detail !== 'string') return false; 
 return detail.toLowerCase().includes('audio disponible solo para sesiones completadas'); 
 } 
 private cleanupAudioRecorder(): void { 
 try { 
 this.mediaRecorder?.stream?.getTracks().forEach((t) => t.stop()); 
 } catch { 
 // ignorar
 } 
 if (this.audioStream) { 
 this.audioStream.getTracks().forEach((t) => t.stop()); 
 } 
 this.mediaRecorder = null; 
 this.audioStream = null; 
 this.audioStartTime = null; 
 } 
 private flushPendingAudioUpload(): void { 
 if (!this.closeCompleted || !this.pendingAudioUpload) return; 
 const { file, durationSeconds } = this.pendingAudioUpload; 
 this.pendingAudioUpload = null; 
 this.uploadSessionAudio(file, durationSeconds); 
 } 
 private sendCancelOnUnload(): void { 
 if (!this.sessionId) return; 
 const url = `${environment.apiUrl}/sessions/${this.sessionId}/close`; 
 const payload = JSON.stringify({ status: 'CANCELADA', motivo: 'ABANDONO' }); 
 const headers: Record<string, string> = { 
 'Content-Type': 'application/json',   }; 
 const token = this.auth.getToken(); 
 if (token) headers.Authorization = `Bearer ${token}`; 
 const csrf = this.readCookie('elvir_csrf_token'); 
 if (csrf) headers['X-CSRF-Token'] = csrf; 
 try { 
 fetch(url, { method: 'POST', headers, body: payload, keepalive: true }); 
 } catch { 
 // ignore
 } 
 } 
 private readCookie(name: string): string | null { 
 const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); 
 const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`)); 
 return match ?  decodeURIComponent(match[1]) : null; 
 } 
 private handleTranscriptEvent(data: any, eventType: string): void { 
 const text = this.extractTranscriptText(data); 
 if (!text) return; 
 const role = this.extractTranscriptRole(data, eventType); 
 const previous = this.captionLines(); 
 const next = [...previous]; 
 if (next.length && this.isTranscriptOverlap(next[next.length - 1], text)) { 
 next[next.length - 1] = text; 
 } else { 
 next.push(text); 
 } 
 this.captionLines.set(next.slice(-2)); 
 this.captionRole.set(role); 
 if (role === 'avatar') { 
 this.upsertChatMessage(text); 
 this.chatAvailable.set(true); 
 } 
 this.captionsAvailable.set(true); 
 if (!this.captionsEnabled()) { 
 this.captionsEnabled.set(true); 
 } 
 } 
 private extractTranscriptText(data: any): string | null { 
 const direct =   data?.text  ??  data?.transcript  ??  data?.transcription  ??  data?.message  ??  data?.content  ??  data?.payload?.text  ??  data?.payload?.transcript  ??  data?.payload?.message  ??  data?.data?.text  ??  data?.data?.transcript  ??  data?.data?.message; 
 if (typeof direct === 'string') { 
 const trimmed = direct.trim(); 
 return trimmed.length ? trimmed : null; 
 } 
 return null; 
 } 
 private upsertChatMessage(text: string): void { 
 const now = Date.now(); 
 const windowMs = 7000; 
 const current = this.chatMessages(); 
 let trimIndex = current.length; 
 while (trimIndex > 0) { 
 const candidate = current[trimIndex - 1]; 
 if (now - candidate.id > windowMs) break; 
 if (this.isTranscriptOverlap(candidate.text, text)) { 
 trimIndex--; 
 continue; 
 } 
 break; 
 } 
 const next = [...current.slice(0, trimIndex), { id: now, text }].slice(-3); 
 this.chatMessages.set(next); 
 } 
 private isTranscriptOverlap(prev: string, next: string): boolean { 
 const a = prev.trim().toLowerCase(); 
 const b = next.trim().toLowerCase(); 
 if (!a || !b) return false; 
 return a === b || a.includes(b) || b.includes(a); 
 } 
 private extractTranscriptRole(data: any, eventType: string): 'user' | 'avatar' | 'system' | null { 
 const raw =   data?.role  ??  data?.speaker  ??  data?.source  ??  data?.payload?.role  ??  data?.payload?.speaker  ??  data?.data?.role  ??  data?.data?.speaker; 
 const normalized = typeof raw === 'string' ?  raw.toLowerCase() : ''; 
 if (normalized.includes('avatar') || normalized.includes('assistant') || normalized.includes('agent')) return 'avatar'; 
 if (normalized.includes('user') || normalized.includes('joven') || normalized.includes('candidate')) return 'user'; 
 if (eventType.startsWith('avatar')) return 'avatar'; 
 if (eventType.startsWith('user')) return 'user'; 
 return null; 
 } 
 private pickAudioMimeType(): string | null { 
 const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg']; 
 for (const type of candidates) { 
 if (MediaRecorder.isTypeSupported(type)) return type; 
 } 
 return null; 
 } 
 private extensionForMime(mimeType: string): string { 
 if (mimeType.includes('ogg')) return 'ogg'; 
 if (mimeType.includes('webm')) return 'webm'; 
 if (mimeType.includes('wav')) return 'wav'; 
 if (mimeType.includes('mp3')) return 'mp3'; 
 if (mimeType.includes('m4a')) return 'm4a'; 
 return 'webm'; 
 }
}

