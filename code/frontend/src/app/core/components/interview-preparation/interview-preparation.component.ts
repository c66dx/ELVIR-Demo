import { CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize } from 'rxjs/operators';
import { SessionApiService } from '@core/services/session-api.service';

interface PrepState {
  companyName?: string;
  companySector?: string;
  companyDescription?: string;
  jobRoleName?: string;
  caseName?: string;
  returnUrl?: string;
}

@Component({
  selector: 'app-interview-preparation',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './interview-preparation.component.html',
  styleUrl: './interview-preparation.component.scss',
})
export class InterviewPreparationComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private sessionsApi = inject(SessionApiService);

  /** Rutas `/joven/.../preparacion` (shell joven); tutor usa `profesional-lobby-shell`. */
  get isJovenFlow(): boolean {
    return this.route.snapshot.data?.['target'] !== 'profesional';
  }

  sessionId = '';
  companyName = 'Empresa colaboradora';
  companySector = 'Servicios empresariales';
  companyDescription = '';
  jobRoleName = 'Entrevista laboral';
  caseName = '';
  contextSummary = 'Esta entrevista simula un entorno laboral real y se enfoca en tus habilidades profesionales.';
  returnUrl: string | null = null;

  cvUploading = false;
  cvUploadError = '';
  cvUploaded = false;
  cvFileName = '';

  recommendations = [
    'Habla con calma y mantén un ritmo natural.',
    'Escucha la pregunta completa antes de responder.',
    'Responde con ejemplos concretos de tu experiencia.',
  ];
  reminders = [
    'Mantén contacto visual con la cámara.',
    'Si necesitas pensar, tómate un segundo.',
    'Respira profundo y confía en tu preparación.',
  ];

  ngOnInit(): void {
    this.sessionId = this.route.snapshot.paramMap.get('sessionId') ?? '';
    this.applyStateData();
    if (this.sessionId) {
      this.loadContextFromApi();
    }
  }

  startInterview(): void {
    if (!this.sessionId) return;
    const target =
      this.route.snapshot.data?.['target'] === 'profesional' ? '/profesional/simulacion' : '/joven/simulacion';
    const state: PrepState = {
      companyName: this.companyName,
      companySector: this.companySector,
      companyDescription: this.companyDescription,
      jobRoleName: this.jobRoleName,
      caseName: this.caseName,
      returnUrl: this.returnUrl ?? undefined,
    };
    this.router.navigate([target, this.sessionId, 'espera'], { state });
  }

  onCvSelected(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (input) input.value = '';
    if (!file || !this.sessionId) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      this.cvUploadError = 'Solo se permiten archivos PDF.';
      return;
    }
    const maxBytes = 10 * 1024 * 1024;
    if (file.size > maxBytes) {
      this.cvUploadError = 'El archivo supera el máximo de 10 MB.';
      return;
    }
    this.cvUploadError = '';
    this.uploadCv(file);
  }

  private uploadCv(file: File): void {
    if (!this.sessionId) return;
    this.cvUploading = true;
    this.sessionsApi
      .uploadSessionCv(this.sessionId, file)
      .pipe(finalize(() => (this.cvUploading = false)))
      .subscribe({
        next: (res) => {
          if ('error' in res) {
            this.cvUploadError = res.error;
            return;
          }
          this.cvUploaded = true;
          this.cvFileName = res.original_name ?? file.name;
        },
        error: () => {
          this.cvUploadError = 'No se pudo subir el CV. Intenta nuevamente.';
        },
      });
  }

  private applyStateData(): void {
    const state = history.state as PrepState | undefined;
    if (state?.companyName) this.companyName = state.companyName;
    if (state?.companySector) this.companySector = state.companySector;
    if (state?.companyDescription) this.companyDescription = state.companyDescription;
    if (state?.jobRoleName) this.jobRoleName = state.jobRoleName;
    if (state?.caseName) this.caseName = state.caseName;
    if (state?.returnUrl) this.returnUrl = state.returnUrl;
    if (!this.contextSummary && state?.companyDescription) {
      this.contextSummary = this.buildContextSummary(state.companyDescription, state.jobRoleName, state.caseName);
    }
  }

  private loadContextFromApi(): void {
    this.sessionsApi.getSessionContext(this.sessionId).subscribe({
      next: (ctx) => {
        if (!ctx) return;
        this.jobRoleName = ctx.jobRoleName ?? this.jobRoleName;
        this.caseName = ctx.caseName ?? this.caseName;
        if (!this.companyName || this.companyName === 'Empresa colaboradora') {
          const company = this.mapCompany(this.jobRoleName);
          this.companyName = company.name;
          this.companySector = company.sector;
          this.companyDescription = this.companyDescription || company.description;
        }
        if (!this.contextSummary) {
          this.contextSummary = this.buildContextSummary(this.companyDescription, this.jobRoleName, this.caseName);
        }
      },
    });
  }

  private mapCompany(jobRoleName?: string | null): { name: string; sector: string; description: string } {
    if (!jobRoleName) {
      return {
        name: 'Empresa colaboradora',
        sector: 'Servicios empresariales',
        description: 'Organización del sector laboral con foco en experiencias reales.',
      };
    }
    const normalized = jobRoleName.toLowerCase();
    if (normalized.includes('operario')) {
      return {
        name: 'Logística Andina',
        sector: 'Logística y bodegaje',
        description: 'Empresa dedicada a la distribución y apoyo en bodegas.',
      };
    }
    if (normalized.includes('atención') || normalized.includes('publico')) {
      return {
        name: 'Centro Ciudadano',
        sector: 'Atención al cliente y servicios',
        description: 'Organización que orienta a personas en servicios y trámites.',
      };
    }
    if (normalized.includes('administrativo')) {
      return {
        name: 'Clínica Horizonte',
        sector: 'Salud y administración',
        description: 'Centro de salud que coordina agenda y documentación interna.',
      };
    }
    if (normalized.includes('técnico') || normalized.includes('tecnico')) {
      return {
        name: 'TecnoSoluciones',
        sector: 'Servicios técnicos',
        description: 'Empresa que implementa soporte y servicios técnicos a clientes.',
      };
    }
    return {
      name: 'Empresa colaboradora',
      sector: 'Servicios empresariales',
      description: 'Organización del sector laboral con foco en experiencias reales.',
    };
  }

  private buildContextSummary(description?: string | null, role?: string | null, caseName?: string | null): string {
    const base = description?.trim() || 'Se trata de una entrevista simulada para reforzar competencias laborales.';
    const roleText = role ? `El foco está en el cargo de ${role}.` : '';
    const caseText = caseName ? `El caso seleccionado es ${caseName}.` : '';
    return [base, roleText, caseText].filter(Boolean).join(' ');
  }
}
