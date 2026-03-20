import { Component, inject, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { forkJoin, EMPTY } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { ApiService } from '../../../../core/services/api.service';
import type { JobRole } from '../../../../core/models/job-role.model';
import type { Case } from '../../../../core/models/case.model';

@Component({
  selector: 'app-supervised-start',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './supervised-start.component.html',
  styleUrl: './supervised-start.component.scss',
})
export class SupervisedStartComponent implements OnInit {
  private fb = inject(FormBuilder);
  private api = inject(ApiService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  form!: FormGroup;
  jobRoles: JobRole[] = [];
  cases: Case[] = [];
  loading = true;
  submitting = false;
  errorMessage = '';

  youthId = '';

  ngOnInit(): void {
    this.youthId = this.route.parent?.snapshot.paramMap.get('youthId') ?? '';
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

  onSubmit(): void {
    if (this.form.invalid) return;

    this.submitting = true;
    this.errorMessage = '';
    const { job_role_id, case_id } = this.form.getRawValue();

    this.api
      .getSimulationTemplates({ job_role_id, case_id })
      .pipe(
        switchMap((templates) => {
          const template = templates[0];
          if (!template) {
            this.errorMessage = 'No se encontró plantilla para esta combinación';
            this.submitting = false;
            return EMPTY;
          }
          return this.api.getMe().pipe(
            switchMap((me) => {
              const professionalId = me?.role === 'PROFESIONAL' ? me.professional_id : undefined;
              return this.api.createSession({
                youth_id: this.youthId,
                simulation_template_id: template.id,
                mode: 'SUPERVISADA',
                professional_id: professionalId,
              });
            })
          );
        })
      )
      .subscribe({
        next: (session) => {
          if (session) {
            const role = this.jobRoles.find((jr) => String(jr.id) === String(job_role_id));
            const caseItem = this.cases.find((c) => String(c.id) === String(case_id));
            this.router.navigate(['/profesional/simulacion', session.id, 'preparacion'], {
              state: {
                returnUrl: `/profesional/jovenes/${this.youthId}`,
                jobRoleName: role?.name ?? '',
                caseName: caseItem?.name ?? '',
              },
            });
          }
          this.submitting = false;
        },
        error: () => {
          this.submitting = false;
        },
      });
  }
}

