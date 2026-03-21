import { Component, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-change-password',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './change-password.component.html',
  styleUrl: './change-password.component.scss',
})
export class ChangePasswordComponent {
  private fb = inject(FormBuilder);
  private api = inject(ApiService);
  private router = inject(Router);
  private notification = inject(NotificationService);

  form: FormGroup = this.fb.nonNullable.group({
    current_password: ['', Validators.required],
    new_password: ['', [Validators.required, Validators.minLength(6)]],
    new_password_confirm: ['', Validators.required],
  });

  submitting = false;
  errorMessage = '';

  onSubmit(): void {
    const v = this.form.getRawValue();
    if (v.new_password !== v.new_password_confirm) {
      this.form.get('new_password_confirm')?.setErrors({ mismatch: true });
      return;
    }
    if (this.form.invalid) return;
    this.errorMessage = '';
    this.submitting = true;
    this.api.changePassword(v.current_password, v.new_password).subscribe({
      next: (result) => {
        this.submitting = false;
        if ('error' in result) {
          this.errorMessage = result.error;
          return;
        }
        this.notification.success('Contraseña actualizada correctamente');
        this.router.navigate(['/']);
      },
      error: () => {
        this.submitting = false;
      },
    });
  }
}

