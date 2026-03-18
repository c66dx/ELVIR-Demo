import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-profesional-form',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './profesional-form.component.html',
  styleUrl: './profesional-form.component.scss',
})
export class ProfesionalFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private api = inject(ApiService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private notification = inject(NotificationService);

  form: FormGroup = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
    display_name: ['', Validators.required],
    specialty: [''],
    institution: [''],
  });

  submitting = false;
  errorMessage = '';

  isEdit = false;
  professionalId: string | null = null;

  ngOnInit(): void {
    this.route.paramMap.subscribe((params) => {
      const id = params.get('professionalId');
      if (id) {
        this.isEdit = true;
        this.professionalId = id;
        // En edición no se gestionan credenciales desde aquí
        const emailCtrl = this.form.get('email');
        const passwordCtrl = this.form.get('password');
        emailCtrl?.clearValidators();
        passwordCtrl?.clearValidators();
        emailCtrl?.disable();
        passwordCtrl?.disable();
        emailCtrl?.updateValueAndValidity({ emitEvent: false });
        passwordCtrl?.updateValueAndValidity({ emitEvent: false });
        this.loadProfessional(id);
      }
    });
  }

  private loadProfessional(id: string): void {
    this.api.getProfessional(id).subscribe((prof) => {
      if (!prof) return;
      this.form.patchValue({
        display_name: prof.display_name,
        specialty: prof.specialty ?? '',
        institution: prof.institution ?? '',
      });
    });
  }

  onSubmit(): void {
    if (this.form.invalid) return;
    this.errorMessage = '';
    this.submitting = true;
    const v = this.form.getRawValue();
    if (this.isEdit && this.professionalId) {
      this.api.updateProfessional(this.professionalId, {
        display_name: v.display_name,
        specialty: v.specialty || undefined,
        institution: v.institution || undefined,
      }).subscribe({
        next: (result) => {
          this.submitting = false;
          if ('error' in result) {
            this.errorMessage = result.error;
            return;
          }
          this.notification.success('Tutor actualizado correctamente');
          this.router.navigate(['/admin/profesionales']);
        },
        error: () => {
          this.submitting = false;
        },
      });
    } else {
      this.api.createProfessional({
        email: v.email,
        password: v.password,
        display_name: v.display_name,
        specialty: v.specialty || undefined,
        institution: v.institution || undefined,
      }).subscribe({
        next: (result) => {
          this.submitting = false;
          if ('error' in result) {
            this.errorMessage = result.error;
            return;
          }
          this.notification.success('Tutor creado correctamente');
          this.router.navigate(['/admin/profesionales']);
        },
        error: () => {
          this.submitting = false;
        },
      });
    }
  }
}

