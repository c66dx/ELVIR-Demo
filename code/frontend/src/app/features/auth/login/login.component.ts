import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ApiService } from '../../../core/services/api.service';

export type LoginRole = 'joven' | 'profesional' | 'admin' | null;

/**
 * Login con selección previa de rol (joven/profesional). Usa ApiService para autenticar contra el backend.
 * y AuthService.setSession para guardar token y rol. Credenciales de prueba en el HTML.
 */
@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private api = inject(ApiService);
  private router = inject(Router);

  form: FormGroup = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  selectedRole: LoginRole = null;
  errorMessage = '';
  loading = false;

  selectRole(role: 'joven' | 'profesional' | 'admin'): void {
    this.selectedRole = role;
    this.errorMessage = '';
  }

  goBack(): void {
    this.selectedRole = null;
    this.errorMessage = '';
  }

  onSubmit(): void {
    if (this.form.invalid) return;

    this.errorMessage = '';
    this.loading = true;
    const { email, password } = this.form.getRawValue();

    this.api.login(email, password).subscribe({
      next: (result) => {
        this.loading = false;
        if ('error' in result) {
          this.errorMessage = result.error;
          return;
        }
        this.auth.setSession(result.access_token, result.role);
        const redirect =
          result.role === 'JOVEN' ? '/joven/dashboard' :
          result.role === 'ADMIN' ? '/admin/dashboard' : '/profesional/dashboard';
        this.router.navigate([redirect]);
      },
      error: () => {
        this.loading = false;
      },
    });
  }
}
