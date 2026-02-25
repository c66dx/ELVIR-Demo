import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';

type ActivateState = 'loading' | 'valid' | 'invalid' | 'success' | 'error';

@Component({
  selector: 'app-activate',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './activate.component.html',
  styleUrl: './activate.component.scss',
})
export class ActivateComponent implements OnInit {
  private fb = inject(FormBuilder);
  private api = inject(ApiService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  state = signal<ActivateState>('loading');
  email = signal<string>('');
  displayName = signal<string>('');
  errorCode = signal<string | null>(null);

  form: FormGroup = this.fb.nonNullable.group({
    password: ['', [Validators.required, Validators.minLength(6)]],
    passwordConfirm: ['', Validators.required],
  });

  private token: string | null = null;

  ngOnInit(): void {
    this.token = this.route.snapshot.queryParamMap.get('token');
    if (!this.token) {
      this.state.set('invalid');
      this.errorCode.set('TOKEN_NOT_FOUND');
      return;
    }
    this.api.validateActivationToken(this.token).subscribe({
      next: (res) => {
        if (res.valid && res.email) {
          this.email.set(res.email);
          this.displayName.set(res.display_name ?? '');
          this.state.set('valid');
        } else {
          this.state.set('invalid');
          this.errorCode.set(res.error ?? 'TOKEN_NOT_FOUND');
        }
      },
      error: () => {
        this.state.set('invalid');
        this.errorCode.set('TOKEN_NOT_FOUND');
      },
    });
  }

  onSubmit(): void {
    if (this.form.invalid || !this.token) return;

    const { password, passwordConfirm } = this.form.getRawValue();
    if (password !== passwordConfirm) {
      this.form.get('passwordConfirm')?.setErrors({ mismatch: true });
      return;
    }

    this.api.activateAccount(this.token, password).subscribe({
      next: (res) => {
        if (res.success) {
          this.state.set('success');
        } else {
          this.state.set('error');
          this.errorCode.set(res.error ?? null);
        }
      },
      error: () => {
        this.state.set('error');
        this.errorCode.set('TOKEN_NOT_FOUND');
      },
    });
  }

  goToLogin(): void {
    this.router.navigate(['/login']);
  }
}
