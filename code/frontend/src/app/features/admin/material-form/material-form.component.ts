import { Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';
import type { MaterialType } from '../../../core/models/types.model';

@Component({
  selector: 'app-material-form',
  standalone: true,
  imports: [AsyncPipe, ReactiveFormsModule, RouterLink],
  templateUrl: './material-form.component.html',
  styleUrl: './material-form.component.scss',
})
export class MaterialFormComponent {
  private fb = inject(FormBuilder);
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private router = inject(Router);
  private notification = inject(NotificationService);

  readonly isAdmin = this.auth.getRole() === 'ADMIN';
  readonly backRoute = this.isAdmin ? '/admin/dashboard' : '/profesional/dashboard';

  readonly types: { value: MaterialType; label: string }[] = [
    { value: 'VIDEO', label: 'Video' },
    { value: 'PDF', label: 'PDF' },
    { value: 'LINK', label: 'Enlace' },
  ];

  form: FormGroup = this.fb.nonNullable.group({
    title: ['', Validators.required],
    description: [''],
    type: ['VIDEO' as MaterialType, Validators.required],
    url: [''],
    job_role_id: [''],
    case_id: [''],
  });

  constructor() {
    this.form.get('type')?.valueChanges.subscribe((t) => {
      if (t === 'LINK') this.selectedFile = null;
    });
  }

  jobRoles$ = this.api.getJobRoles();
  cases$ = this.api.getCases();

  submitting = false;
  errorMessage = '';
  /** Archivo seleccionado para subir (VIDEO o PDF). */
  selectedFile: File | null = null;

  get canUploadFile(): boolean {
    const t = this.form.get('type')?.value;
    return t === 'VIDEO' || t === 'PDF';
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    this.selectedFile = file ?? null;
    if (this.selectedFile) {
      this.form.patchValue({ url: '' });
    }
    input.value = '';
  }

  clearFile(): void {
    this.selectedFile = null;
  }

  onSubmit(): void {
    const v = this.form.getRawValue();
    const urlOrFile = this.selectedFile ? null : (v.url || '').trim();
    if (!urlOrFile && !this.selectedFile) {
      this.errorMessage = this.canUploadFile
        ? 'Indica una URL o sube un archivo'
        : 'La URL es obligatoria';
      return;
    }
    if (!this.canUploadFile && !urlOrFile) {
      this.errorMessage = 'La URL es obligatoria';
      return;
    }
    this.errorMessage = '';
    this.submitting = true;

    const doCreate = (url: string) => {
      this.api.createSupportMaterial({
        title: v.title,
        description: v.description || undefined,
        type: v.type,
        url,
        job_role_id: v.job_role_id || undefined,
        case_id: v.case_id || undefined,
      }).subscribe({
        next: (result) => {
          this.submitting = false;
          if ('error' in result) {
            this.errorMessage = result.error;
            return;
          }
          this.notification.success('Material creado correctamente');
          const role = this.auth.getRole();
          this.router.navigate([role === 'ADMIN' ? '/admin/dashboard' : '/profesional/dashboard']);
        },
        error: () => {
          this.submitting = false;
        },
      });
    };

    if (this.selectedFile) {
      this.api.uploadFile(this.selectedFile).subscribe({
        next: (res) => {
          if ('error' in res) {
            this.submitting = false;
            this.errorMessage = res.error;
            return;
          }
          doCreate(res.url);
        },
        error: () => {
          this.submitting = false;
        },
      });
    } else {
      doCreate(urlOrFile);
    }
  }
}
