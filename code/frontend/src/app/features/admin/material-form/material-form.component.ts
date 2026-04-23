import { Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { CatalogApiService } from '@core/services/catalog-api.service';
import { MaterialApiService } from '@core/services/material-api.service';
import { AuthService } from '@core/services/auth.service';
import { NotificationService } from '@core/services/notification.service';
import type { MaterialType } from '@core/models/types.model';
import { FormContainerComponent } from '@shared/form/form-container/form-container.component';
import { FormSectionComponent } from '@shared/form/form-section/form-section.component';
import { FormGridComponent } from '@shared/form/form-grid/form-grid.component';
import { FormFieldComponent } from '@shared/form/form-field/form-field.component';
import { FormActionsComponent } from '@shared/form/form-actions/form-actions.component';
import { TextInputComponent } from '@shared/form/inputs/text-input/text-input.component';
import { TextareaInputComponent } from '@shared/form/inputs/textarea-input/textarea-input.component';
import { SelectInputComponent } from '@shared/form/inputs/select-input/select-input.component';

/** Alineado con `app.services.upload_files` (backend). */
const MATERIAL_MAX_BYTES = 50 * 1024 * 1024;
const MATERIAL_ALLOWED_EXT = new Set(['.pdf', '.mp4', '.webm', '.mov', '.avi', '.mkv']);

@Component({
  selector: 'app-material-form',
  standalone: true,
  imports: [
    AsyncPipe,
    ReactiveFormsModule,
    RouterLink,
    FormContainerComponent,
    FormSectionComponent,
    FormGridComponent,
    FormFieldComponent,
    FormActionsComponent,
    TextInputComponent,
    TextareaInputComponent,
    SelectInputComponent,
  ],
  templateUrl: './material-form.component.html',
  styleUrl: './material-form.component.scss',
})
export class MaterialFormComponent {
  private fb = inject(FormBuilder);
  private catalogApi = inject(CatalogApiService);
  private materialsApi = inject(MaterialApiService);
  private auth = inject(AuthService);
  private router = inject(Router);
  private notification = inject(NotificationService);

  readonly isAdmin = this.auth.getRole() === 'ADMIN';
  readonly isTutorArea = this.auth.getRole() === 'PROFESIONAL';
  readonly backRoute = this.isAdmin ? '/admin/material' : '/profesional/material';
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

  jobRoles$ = this.catalogApi.getJobRoles();
  cases$ = this.catalogApi.getCases();
  submitting = false;
  errorMessage = '';
  /** 0–100 durante subida; -1 si el navegador no informa total; null si no hay subida activa. */
  uploadProgress: number | null = null;

  /** Archivo seleccionado para subir (VIDEO o PDF). */
  selectedFile: File | null = null;

  get canUploadFile(): boolean {
    const t = this.form.get('type')?.value;
    return t === 'VIDEO' || t === 'PDF';
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.errorMessage = '';
    if (!file) {
      this.selectedFile = null;
      input.value = '';
      return;
    }
    const lower = file.name.toLowerCase();
    const dot = lower.lastIndexOf('.');
    const ext = dot >= 0 ? lower.slice(dot) : '';
    if (!MATERIAL_ALLOWED_EXT.has(ext)) {
      this.errorMessage = `Formato no permitido. Usa: ${Array.from(MATERIAL_ALLOWED_EXT).sort().join(', ')}`;
      this.selectedFile = null;
      input.value = '';
      return;
    }
    if (file.size > MATERIAL_MAX_BYTES) {
      this.errorMessage = 'El archivo supera el máximo de 50 MB';
      this.selectedFile = null;
      input.value = '';
      return;
    }
    this.selectedFile = file;
    this.form.patchValue({ url: '' });
    input.value = '';
  }

  clearFile(): void {
    this.selectedFile = null;
  }

  onSubmit(): void {
    const v = this.form.getRawValue();
    const urlOrFile = this.selectedFile ? null : (v.url || '').trim();
    if (!urlOrFile && !this.selectedFile) {
      this.errorMessage = this.canUploadFile ? 'Indica una URL o sube un archivo' : 'La URL es obligatoria';
      return;
    }
    if (!this.canUploadFile && !urlOrFile) {
      this.errorMessage = 'La URL es obligatoria';
      return;
    }
    this.errorMessage = '';
    this.submitting = true;
    this.uploadProgress = null;

    const doCreate = (url: string) => {
      this.materialsApi
        .createSupportMaterial({
          title: v.title,
          description: v.description || undefined,
          type: v.type,
          url,
          job_role_id: v.job_role_id || undefined,
          case_id: v.case_id || undefined,
        })
        .subscribe({
          next: (result) => {
            this.submitting = false;
            this.uploadProgress = null;
            if ('error' in result) {
              this.errorMessage = result.error;
              return;
            }
            this.notification.success('Material creado correctamente');
            const role = this.auth.getRole();
            this.router.navigate([role === 'ADMIN' ? '/admin/material' : '/profesional/material']);
          },
          error: () => {
            this.submitting = false;
            this.uploadProgress = null;
          },
        });
    };

    if (this.selectedFile) {
      this.uploadProgress = 0;
      this.materialsApi.uploadFile(this.selectedFile).subscribe({
        next: (res) => {
          if ('progress' in res) {
            this.uploadProgress = res.progress;
            return;
          }
          if ('error' in res) {
            this.submitting = false;
            this.uploadProgress = null;
            this.errorMessage = res.error;
            return;
          }
          this.uploadProgress = null;
          doCreate(res.url);
        },
        error: () => {
          this.submitting = false;
          this.uploadProgress = null;
          this.errorMessage = 'Error de red al subir el archivo. Comprueba la conexión e inténtalo de nuevo.';
        },
      });
    } else {
      doCreate(urlOrFile!);
    }
  }
}


