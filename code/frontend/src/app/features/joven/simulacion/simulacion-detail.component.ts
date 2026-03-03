import { Component, inject, OnDestroy, OnInit, signal, ViewChild, ElementRef } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Room, RoomEvent, RemoteTrack } from 'livekit-client';
import { ApiService } from '../../../core/services/api.service';
import { SessionEndService } from '../../../core/services/session-end.service';
import type { InterviewSummary } from '../../../core/models/interview-summary.model';
import { formatDate, formatDuration, formatStatusLabel } from '../../../shared/utils/date-format.util';

/**
 * Pantalla de simulación en curso. Muestra LiveKit (avatar video/audio) cuando está
 * configurado, o iframe placeholder en caso contrario. Incluye contador, cargo/caso
 * y botones para finalizar/cancelar/simular errores.
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
  private sessionEndService = inject(SessionEndService);

  @ViewChild('avatarVideo') avatarVideoRef?: ElementRef<HTMLVideoElement>;
  @ViewChild('avatarAudio') avatarAudioRef?: ElementRef<HTMLAudioElement>;

  sessionId = '';
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

  private startTime: number | null = null;
  private timerInterval: ReturnType<typeof setInterval> | null = null;
  elapsedTime = signal('0:00');
  private room: Room | null = null;
  private avatarIsSpeaking = false;
  /** True si el navegador bloqueó el audio (autoplay policy) y el usuario debe hacer clic. */
  audioBlocked = signal(false);

  /** True si la sesión ya está finalizada (COMPLETADA/CANCELADA/ERROR) → mostrar resumen, no iniciar. */
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
    this.api.getSessionSummary(this.sessionId).subscribe({
      next: (summary) => summary && this.completedSessionSummary.set(summary),
    });
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

          if (result.livekit_url && result.access_token) {
            this.useLiveKit.set(true);
            this.embedUrl.set(null);
            setTimeout(() => this.connectToLiveKit(result.livekit_url!, result.access_token!), 150);
          } else if (result.embed?.url) {
            this.useLiveKit.set(false);
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
        this.error.set('Error al iniciar la sesión');
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
          audioEl.muted = false;
          audioEl.volume = 1;
          const checkAndPlay = () => {
            if (audioEl.readyState >= 2) {
              audioEl.play().then(() => this.audioBlocked.set(false)).catch(() => {
                this.audioBlocked.set(true);
              });
            } else {
              setTimeout(checkAndPlay, 100);
            }
          };
          checkAndPlay();
        }
      });

      this.room.on(RoomEvent.DataReceived, (payload: Uint8Array) => {
        try {
          const data = JSON.parse(new TextDecoder().decode(payload));
          const eventType = data?.event_type;
          if (!eventType) return;
          if (eventType === 'user.speak_started' && !this.avatarIsSpeaking) {
            this.turnIndicator.set('🎤 Te escuchamos');
          } else if (eventType === 'user.speak_ended' && !this.avatarIsSpeaking) {
            this.turnIndicator.set('🤖 Procesando...');
          } else if (eventType === 'user.transcription' && !this.avatarIsSpeaking) {
            this.turnIndicator.set('🤖 Analizando respuesta...');
          } else if (eventType === 'avatar.speak_started') {
            this.avatarIsSpeaking = true;
            this.turnIndicator.set('🗣 Hablando Javiera');
            this.room?.localParticipant.setMicrophoneEnabled(false);
          } else if (eventType === 'avatar.speak_ended') {
            this.avatarIsSpeaking = false;
            this.turnIndicator.set('🎧 Escuchando...');
            this.room?.localParticipant.setMicrophoneEnabled(true);
          }
        } catch {
          // ignorar
        }
      });

      await this.room.connect(url, token);
      await this.room.localParticipant.setMicrophoneEnabled(true);
      this.sendCommandToAvatar('avatar.start_listening');
      this.turnIndicator.set('🎧 Escuchando...');
    } catch (err) {
      this.error.set('Error al conectar con LiveAvatar');
      this.connectionErrorBanner.set(true);
      this.useLiveKit.set(false);
    }
  }

  onActivarAudio(): void {
    const audioEl = this.avatarAudioRef?.nativeElement;
    if (audioEl?.srcObject) {
      audioEl.play().then(() => this.audioBlocked.set(false)).catch(() => {});
    }
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
    this.router.navigate(['/joven/simulacion/nueva']);
  }

  onSalirConnectionError(): void {
    if (!confirm('¿Salir sin completar la simulación? Se registrará como error de conexión.')) return;
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
    this.startTime = Date.now();
    this.elapsedTime.set('0:00');
    this.timerInterval = setInterval(() => {
      if (!this.startTime) return;
      const sec = Math.floor((Date.now() - this.startTime) / 1000);
      const m = Math.floor(sec / 60);
      const s = sec % 60;
      this.elapsedTime.set(`${m}:${s.toString().padStart(2, '0')}`);
    }, 1000);
  }

  private stopTimer(): void {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  ngOnDestroy(): void {
    this.stopTimer();
    if (this.room) {
      this.room.disconnect();
      this.room = null;
    }
  }

  readonly formatDate = formatDate;
  readonly formatDuration = formatDuration;
  readonly formatStatusLabel = formatStatusLabel;

  closeSession(status: 'COMPLETADA' | 'CANCELADA' | 'ERROR', motivo?: string): void {
    if (status === 'CANCELADA' && !confirm('¿Estás seguro de que quieres cancelar esta simulación? Se registrará como cancelada.')) {
      return;
    }
    if (status === 'ERROR' && !confirm('¿Registrar esta sesión como error? (solo para pruebas)')) {
      return;
    }
    const durationSec = this.startTime ? Math.floor((Date.now() - this.startTime) / 1000) : undefined;
    this.stopTimer();
    const metrics = status === 'COMPLETADA' ? { turn_count: 5, duration_seconds: durationSec } : undefined;
    const youthId = this.youthId();
    const ctx = this.sessionContext();
    this.api.closeSession(this.sessionId, { status, metrics, motivo }).subscribe({
      next: (session) => {
        const returnUrl = history.state?.['returnUrl'] as string | undefined;
        const sessionSummary =
          status === 'COMPLETADA' && (session?.duration_seconds || ctx)
            ? {
                duration_seconds: session?.duration_seconds,
                jobRoleName: ctx?.jobRoleName,
                caseName: ctx?.caseName,
                sessionId: this.sessionId,
              }
            : undefined;
        this.sessionEndService.set({
          status,
          motivo,
          returnUrl,
          youthId: youthId ?? undefined,
          sessionSummary,
        });
        this.router.navigate(['/session-end']);
      },
    });
  }
}
