import { Component, inject, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import {
  SessionEndService,
  type SessionEndData,
} from '../../../../core/services/session-end.service';
import type { SessionStatus } from '../../../../core/models/types.model';
import { formatDuration } from '../../../../shared/utils/date-format.util';

type SessionSummary = NonNullable<SessionEndData['sessionSummary']>;

/** Pantalla post-simulación: muestra estado (COMPLETADA/CANCELADA/ERROR), resumen y enlaces. */
@Component({
  selector: 'app-session-end',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './session-end.component.html',
  styleUrl: './session-end.component.scss',
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
    this.status = data?.status ?? null;
    this.motivo = data?.motivo ?? null;
    this.youthId = data?.youthId ?? null;
    this.sessionSummary = data?.sessionSummary ?? null;
    const role = this.auth.getRole();
    this.isJoven = role === 'JOVEN';
    this.isProfesional = role === 'PROFESIONAL';
    if (!this.status) {
      this.router.navigateByUrl(this.isProfesional ? '/profesional/dashboard' : '/joven/dashboard');
    }
  }

  get title(): string {
    switch (this.status) {
      case 'COMPLETADA':
        return 'Sesión completada';
      case 'CANCELADA':
        return 'Sesión cancelada';
      case 'ERROR':
        return 'Sesión finalizada con error';
      default:
        return 'Sesión finalizada';
    }
  }

  get variant(): 'success' | 'warning' | 'error' {
    switch (this.status) {
      case 'COMPLETADA':
        return 'success';
      case 'CANCELADA':
        return 'warning';
      case 'ERROR':
        return 'error';
      default:
        return 'warning';
    }
  }

  onVolver(): void {
    const data = this.sessionEndService.get();
    const returnUrl = data?.returnUrl;
    const target = returnUrl ?? (this.isProfesional ? '/profesional/dashboard' : '/joven/dashboard');
    this.sessionEndService.clear();
    this.router.navigateByUrl(target);
  }

  readonly formatDuration = formatDuration;
}

