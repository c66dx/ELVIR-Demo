import { Component, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-profesional-form',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './profesional-form.component.html',
  styleUrl: './profesional-form.component.scss',
})
export class ProfesionalFormComponent {
  private fb = inject(FormBuilder);
  private api = inject(ApiService);
  private router = inject(Router);
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

  onSubmit(): void {
    if (this.form.invalid) return;
    this.errorMessage = '';
    this.submitting = true;
    const v = this.form.getRawValue();
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
        this.notification.success('Profesional creado correctamente');
        this.router.navigate(['/admin/profesionales']);
      },
      error: () => {
        this.submitting = false;
        this.errorMessage = 'Error de conexión';
      },
    });
  }
}
