import { Component, inject, OnDestroy, OnInit, signal, ViewChild, ElementRef } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Room, RoomEvent, RemoteTrack } from 'livekit-client';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { SessionEndService } from '../../../core/services/session-end.service';
import { SimulacionRuntimeService } from './simulacion-runtime.service';
import type { InterviewSummary } from '../../../core/models/interview-summary.model';
import { formatDate, formatDuration, formatStatusLabel } from '../../../shared/utils/date-format.util';

/**
 * Pantalla de simulación en curso. Muestra LiveKit (avatar video/audio) cuando está
 * configurado, o iframe placeholder en caso contrario. Incluye contador, cargo/caso
 * y botones para finalizar/cancelar.
 */
@Component({
  selector: 'app-simulacion-detail',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './simulacion-detail.component.html',
  styleUrl: './simulacion-detail.component.scss',
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
  turnIndicator = signal('⏳ Esperando...');
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
  /** Verdadero si el navegador bloqueó el audio (politica de autoplay) y el usuario debe hacer clic. */
  audioBlocked = signal(false);
  /** Muestra una guía inicial para activar audio (solo al inicio). */
  audioHintVisible = signal(false);
  audioReady = signal(false);
  volume = signal(0.8);
  muted = signal(false);

  audioRecording = signal<'idle' | 'recording' | 'stopped' | 'error'>('idle');
  audioRecordingError = signal<string | null>(null);
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private audioStream: MediaStream | null = null;
  private audioStartTime: number | null = null;
  private audioUploaded = false;

  /** Verdadero si la sesion ya esta finalizada (COMPLETADA/CANCELADA/ERROR) -> mostrar resumen, no iniciar. */
  sessionCompleted = signal(false);
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
    this.sessionId = this.route.snapshot.paramMap.get('sessionId') ?? '';
    this.isProfessionalView.set(this.auth.getRole() === 'PROFESIONAL');
    const returnUrl = history.state?.['returnUrl'] as string | undefined;
    this.returnUrl.set(returnUrl && returnUrl.startsWith('/') ? returnUrl : null);
    if (!this.sessionId) return;

    this.api.getSession(this.sessionId).subscribe({
      next: (s) => {
        if (s) {
          this.sessionMode.set(s.mode);
          this.youthId.set(s.youth_id);
          const isFinalizada = s.status === 'COMPLETADA' || s.status === 'CANCELADA' || s.status === 'ERROR';
          if (isFinalizada) {
            this.sessionCompleted.set(true);
            this.loading.set(false);
            this.loadSessionContextForCompleted();
            this.completedSessionData.set({
              status: s.status,
              started_at: s.started_at,
              ended_at: s.ended_at,
              duration_seconds: s.duration_seconds,
              mode: s.mode,
            });
            return;
          }
        }
        this.doStartSession();
      },
      error: () => {
        this.loading.set(false);
        this.sessionNotFound.set(true);
      },
    });
  }

  private loadSessionContextForCompleted(): void {
    this.api.getSessionContext(this.sessionId).subscribe({
      next: (ctx) => {
        if (ctx) {
          this.completedSessionData.update((d) =>
            d ? { ...d, jobRoleName: ctx.jobRoleName, caseName: ctx.caseName } : d
          );
        }
      },
    });
    if (this.isProfessionalView()) {
      this.api.getSessionSummary(this.sessionId).subscribe({
        next: (summary) => summary && this.completedSessionSummary.set(summary),
      });
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
          this.startAudioRecording();

        if (result.livekit_url && result.access_token) {
          this.useLiveKit.set(true);
          this.audioHintVisible.set(true);
          this.embedUrl.set(null);
          setTimeout(() => this.connectToLiveKit(result.livekit_url!, result.access_token!), 150);
        } else if (result.embed?.url) {
          this.useLiveKit.set(false);
          this.audioHintVisible.set(false);
          this.embedUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(result.embed.url));
        } else {
            this.connectionErrorBanner.set(true);
            this.error.set('Respuesta inválida del servidor');
          }
        } else {
          this.sessionNotFound.set(true);
          this.error.set(null);
          this.connectionErrorBanner.set(false);
        }
      },
      error: () => {
        this.loading.set(false);
        this.retrying.set(false);
        this.error.set('Error al iniciar la entrevista');
        this.connectionErrorBanner.set(true);
      },
    });
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
          // Intentar autoplay; si el navegador lo bloquea, mostramos el botón de activación.
          this.audioBlocked.set(true);
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
          if (!eventType) return;
          if (eventType === 'user.speak_started' && !this.avatarIsSpeaking) {
            this.turnIndicator.set('Te escuchamos');
          } else if (eventType === 'user.speak_ended' && !this.avatarIsSpeaking) {
            this.turnIndicator.set('Procesando...');
          } else if (eventType === 'user.transcription' && !this.avatarIsSpeaking) {
            this.turnIndicator.set('Analizando respuesta...');
          } else if (eventType === 'avatar.speak_started') {
            this.avatarIsSpeaking = true;
            this.turnIndicator.set('Hablando Javiera');
            this.room?.localParticipant.setMicrophoneEnabled(false);
          } else if (eventType === 'avatar.speak_ended') {
            this.avatarIsSpeaking = false;
            this.turnIndicator.set('Escuchando...');
            this.room?.localParticipant.setMicrophoneEnabled(true);
          }
        } catch {
          // ignorar
        }
      });

      await this.room.connect(url, token);
      await this.room.localParticipant.setMicrophoneEnabled(true);
      this.sendCommandToAvatar('avatar.start_listening');
      this.turnIndicator.set('Escuchando...');
    } catch (err) {
      this.error.set('Error al conectar con LiveAvatar');
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
    const value = Number(target?.value ?? this.volume());
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
      this.room.localParticipant.publishData(
        new TextEncoder().encode(JSON.stringify({ type, payload })),
        { reliable: true, topic: 'agent-control' }
      );
    } catch {
      // ignorar
    }
  }

  loadSessionContext(): void {
    this.api.getSessionContext(this.sessionId).subscribe({
      next: (ctx) => ctx && this.sessionContext.set(ctx),
    });
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
    this.stopAudioRecording(true);
    const youthId = this.youthId();
    this.api.closeSession(this.sessionId, { status: 'ERROR', motivo: 'LIVEAVATAR_CONNECTION' }).subscribe({
      next: () => {
        const returnUrl = history.state?.['returnUrl'] as string | undefined;
        this.sessionEndService.set({
          status: 'ERROR',
          motivo: 'LIVEAVATAR_CONNECTION',
          returnUrl,
          youthId: youthId ?? undefined,
        });
        this.router.navigate(['/session-end']);
      },
    });
  }

  private startTimer(): void {
    this.simulacionRuntime.startTimer((label) => this.elapsedTime.set(label));
  }

  private stopTimer(): void {
    this.simulacionRuntime.stopTimer();
  }

  ngOnDestroy(): void {
    this.stopTimer();
    this.stopAudioRecording(true);
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
      return this.returnUrl() ?? '/profesional/jovenes';
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
      return this.returnUrl() ? 'Volver a ficha' : 'Volver al listado';
    }
    return 'Volver a entrevista';
  }

  secondaryReturnLabel(): string {
    return this.isProfessionalView() ? 'Ver entrevistas' : 'Ver historial';
  }

  completedTitle(): string {
    return this.isProfessionalView() ? 'La entrevista del joven finalizó' : 'Tu entrevista finalizó';
  }

  completedSubtitle(): string {
    return this.isProfessionalView()
      ? 'Revisa el detalle de la entrevista o vuelve a la ficha del joven.'
      : 'Revisa el detalle de la entrevista y la retroalimentacion del tutor cuando este disponible.';
  }

  summaryTitle(): string {
    return this.isProfessionalView() ? 'Resumen del tutor' : 'Feedback del tutor';
  }

  summaryEmptyText(): string {
    return this.isProfessionalView()
      ? 'Aún no se registra feedback para esta entrevista.'
      : 'Tu tutor aún no deja feedback para esta entrevista.';
  }

  closeSession(status: 'COMPLETADA' | 'CANCELADA', motivo?: string): void {
    if (status === 'CANCELADA' && !confirm('¿Estás seguro de que quieres cancelar esta entrevista? Se registrará como cancelada.')) {
      return;
    }
    this.stopAudioRecording(true);
    const metrics = this.simulacionRuntime.buildCloseMetrics(status);
    this.stopTimer();
    const youthId = this.youthId();
    const ctx = this.sessionContext();
    this.api.closeSession(this.sessionId, { status, metrics, motivo }).subscribe({
      next: (session) => {
        const returnUrl = history.state?.['returnUrl'] as string | undefined;
        this.sessionEndService.set(
          this.simulacionRuntime.buildSessionEndData({
            status,
            motivo,
            returnUrl,
            youthId: youthId ?? undefined,
            session,
            context: ctx,
            sessionId: this.sessionId,
          })
        );
        this.router.navigate(['/session-end']);
      },
    });
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
      this.mediaRecorder = new MediaRecorder(
        this.audioStream,
        mimeType ? { mimeType } : undefined
      );
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
        this.uploadSessionAudio(result.file, result.durationSeconds);
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
    const durationSeconds =
      this.audioStartTime != null ? Math.round((performance.now() - this.audioStartTime) / 1000) : undefined;
    return { file, durationSeconds };
  }

  private uploadSessionAudio(file: File, durationSeconds?: number): void {
    if (!this.sessionId || this.audioUploaded) return;
    this.audioUploaded = true;
    this.api.uploadSessionAudio(this.sessionId, file, durationSeconds).subscribe({
      next: (res) => {
        if ('error' in res) {
          this.audioUploaded = false;
          this.audioRecordingError.set(res.error);
        }
      },
      error: () => {
        this.audioUploaded = false;
        this.audioRecordingError.set('Error al subir el audio.');
      },
    });
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

