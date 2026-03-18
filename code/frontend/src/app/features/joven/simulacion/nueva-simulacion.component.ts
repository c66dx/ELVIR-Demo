import { Component, inject, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { forkJoin, EMPTY } from 'rxjs';
import { switchMap, finalize } from 'rxjs/operators';
import { YouthService } from '../../../core/services/youth.service';
import { ApiService } from '../../../core/services/api.service';
import type { JobRole } from '../../../core/models/job-role.model';
import type { Case } from '../../../core/models/case.model';
import type { SimulationTemplate } from '../../../core/models/simulation-template.model';

/**
 * Formulario para elegir cargo y caso. Crea sesión AUTOGESTIONADA y navega a la simulación.
 * Usa la primera plantilla que coincida con la combinación seleccionada.
 */
@Component({
  selector: 'app-nueva-simulacion',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './nueva-simulacion.component.html',
  styleUrl: './nueva-simulacion.component.scss',
})
export class NuevaSimulacionComponent implements OnInit {
  private fb = inject(FormBuilder);
  private youthService = inject(YouthService);
  private api = inject(ApiService);
  private router = inject(Router);

  form!: FormGroup;
  jobRoles: JobRole[] = [];
  cases: Case[] = [];
  loading = true;
  submitting = false;
  errorMessage = '';
  private readonly companyContexts: Record<string, { name: string; description: string }> = {
    operario: {
      name: 'Logistica Andina',
      description: 'una empresa dedicada a la distribucion y apoyo en bodegas.',
    },
    'atencion-publico': {
      name: 'Centro Ciudadano',
      description: 'una organizacion que orienta a personas en servicios y tramites.',
    },
    administrativo: {
      name: 'Clinica Horizonte',
      description: 'un centro de salud que coordina agenda y documentacion interna.',
    },
    'tecnico-profesional': {
      name: 'TecnoSoluciones',
      description: 'una empresa que implementa soporte y servicios tecnicos a clientes.',
    },
  };

  ngOnInit(): void {
    this.form = this.fb.nonNullable.group({
      job_role_id: ['', Validators.required],
      case_id: ['', Validators.required],
    });

    forkJoin({
      jobRoles: this.api.getJobRoles(),
      cases: this.api.getCases(),
    }).subscribe({
      next: ({ jobRoles, cases }) => {
        this.jobRoles = jobRoles;
        this.cases = cases;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  selectedJobRole(): JobRole | null {
    if (!this.form) return null;
    const id = this.form.get('job_role_id')?.value;
    if (!id) return null;
    return this.jobRoles.find((jr) => String(jr.id) === String(id)) ?? null;
  }

  selectedCase(): Case | null {
    if (!this.form) return null;
    const id = this.form.get('case_id')?.value;
    if (!id) return null;
    return this.cases.find((c) => String(c.id) === String(id)) ?? null;
  }

  getCompanyContext(role: JobRole | null): { name: string; description: string } {
    if (!role) return { name: 'una empresa', description: 'una organizacion del sector laboral.' };
    return this.companyContexts[role.slug] ?? {
      name: 'una empresa',
      description: 'una organizacion del sector laboral.',
    };
  }

  onSubmit(): void {
    if (this.form.invalid) return;

    this.submitting = true;
    this.errorMessage = '';
    const { job_role_id, case_id } = this.form.getRawValue();

    this.youthService
      .getCurrentYouthId()
      .pipe(
        switchMap((youthId) => {
          if (!youthId) {
            this.errorMessage = 'No se pudo identificar al joven';
            return EMPTY;
          }
          return this.api.getSimulationTemplates({ job_role_id, case_id }).pipe(
            switchMap((templates) => {
              const template = templates[0];
              if (!template) {
                this.errorMessage = 'No se encontró plantilla para esta combinación';
                return EMPTY;
              }
              return this.api.createSession({
                youth_id: youthId,
                simulation_template_id: template.id,
                mode: 'AUTOGESTIONADA',
              });
            })
          );
        }),
        finalize(() => (this.submitting = false))
      )
      .subscribe({
        next: (session) => {
          if (session) {
            this.router.navigate(['/joven/simulacion', session.id]);
          }
        },
        error: () => {
          this.submitting = false;
        },
      });
  }
}

