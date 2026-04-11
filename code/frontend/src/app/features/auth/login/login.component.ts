import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '@core/services/auth.service';
import { AuthApiService } from '@core/services/auth-api.service';
import { ThemeService } from '@core/services/theme.service';
import { FormFieldComponent } from '@shared/form/form-field/form-field.component';
import { TextInputComponent } from '@shared/form/inputs/text-input/text-input.component';
import { environment } from '../../../../environments/environment';

export type LoginRole = 'joven' | 'profesional' | 'admin' | null;

/** Login con selección previa de rol. Credenciales de prueba: `environment.demoCredentials`. */
@Component({ 
 selector: 'app-login',   standalone: true,   imports: [CommonModule, ReactiveFormsModule, FormFieldComponent, TextInputComponent],   templateUrl: './login.component.html',   styleUrl: './login.component.scss',
})
export class LoginComponent { 
 private fb = inject(FormBuilder); 
 private auth = inject(AuthService); 
 private authApi = inject(AuthApiService); 
 private router = inject(Router); 
 private themeService = inject(ThemeService); 
 theme = this.themeService.theme;
 readonly demoCredentials = environment.demoCredentials;
 form: FormGroup = this.fb.nonNullable.group({ 
 email: ['', [Validators.required, Validators.email]],   password: ['', Validators.required],   }); 
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
 this.authApi.login(email, password).subscribe({ 
 next: (result) => { 
 this.loading = false; 
 if ('error' in result) { 
 this.errorMessage = result.error; 
 return; 
 } 
 this.auth.setSession(result.access_token, result.role); 
 const redirect =   result.role === 'JOVEN' ? '/joven/simulacion/nueva' :   result.role === 'ADMIN' ? '/admin/dashboard' : '/profesional/dashboard'; 
 this.router.navigate([redirect]); 
 },   error: () => { 
 this.loading = false; 
 },   }); 
 } 
 toggleTheme(): void { 
 this.themeService.toggle(); 
 }
}



