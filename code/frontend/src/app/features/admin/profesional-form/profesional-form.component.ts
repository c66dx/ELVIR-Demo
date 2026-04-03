import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { NotificationService } from '../../../core/services/notification.service';
import { FormActionsComponent } from '../../../shared/form/form-actions/form-actions.component';
import { FormContainerComponent } from '../../../shared/form/form-container/form-container.component';
import { FormFieldComponent } from '../../../shared/form/form-field/form-field.component';
import { FormGridComponent } from '../../../shared/form/form-grid/form-grid.component';
import { FormSectionComponent } from '../../../shared/form/form-section/form-section.component';
import { TextInputComponent } from '../../../shared/form/inputs/text-input/text-input.component';
import { UploadUrlPipe } from '../../../core/pipes/upload-url.pipe';

@Component({
  selector: 'app-profesional-form',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    FormContainerComponent,
    FormSectionComponent,
    FormGridComponent,
    FormFieldComponent,
    FormActionsComponent,
    TextInputComponent,
    UploadUrlPipe,
  ],
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
    display_name: ['', Validators.required],
    specialty: [''],
    institution: [''],
  });

  submitting = false;
  errorMessage = '';
  activationUrl: string | null = null;
  isEdit = false;
  professionalId: string | null = null;
  professional: {
    id: string;
    display_name: string;
    specialty?: string;
    institution?: string;
    is_active: boolean;
    profile_photo_url?: string;
  } | null = null;

  ngOnInit(): void {
    this.route.paramMap.subscribe((params) => {
      const id = params.get('professionalId');
      if (id) {
        this.isEdit = true;
        this.professionalId = id;
        // En edición no se gestionan credenciales desde aquí
        const emailCtrl = this.form.get('email');
        emailCtrl?.clearValidators();
        emailCtrl?.disable();
        emailCtrl?.updateValueAndValidity({ emitEvent: false });
        this.loadProfessional(id);
      }
    });
  }

  private loadProfessional(id: string): void {
    this.api.getProfessional(id).subscribe((prof) => {
      if (!prof) return;
      this.professional = {
        id: prof.id,
        display_name: prof.display_name,
        specialty: prof.specialty ?? undefined,
        institution: prof.institution ?? undefined,
        is_active: prof.is_active,
        profile_photo_url: prof.profile_photo_url ?? undefined,
      };
      this.form.patchValue({
        display_name: prof.display_name,
        specialty: prof.specialty ?? '',
        institution: prof.institution ?? '',
      });
    });
  }

  toggleActive(): void {
    if (!this.professionalId || !this.professional) return;
    const nextActive = !this.professional.is_active;
    const label = nextActive ? 'Reactivar' : 'Desactivar';
    if (!confirm(`¿${label} a ${this.professional.display_name}?`)) return;
    const v = this.form.getRawValue();
    this.api
      .updateProfessional(this.professionalId, {
        display_name: v.display_name,
        specialty: v.specialty || undefined,
        institution: v.institution || undefined,
        is_active: nextActive,
      })
      .subscribe({
        next: (result) => {
          if ('error' in result) {
            this.notification.error(result.error);
            return;
          }
          this.professional!.is_active = nextActive;
          this.notification.success(nextActive ? 'Tutor reactivado' : 'Tutor desactivado');
        },
        error: () => this.notification.error('No se pudo actualizar el estado del tutor'),
      });
  }

  deleteProfessional(): void {
    if (!this.professionalId || !this.professional) return;
    if (!confirm(`¿Eliminar a ${this.professional.display_name}? Esta acción no se puede deshacer.`)) return;
    this.api.deleteProfessionalAsAdmin(this.professionalId).subscribe({
      next: (res) => {
        if ('error' in res) {
          this.notification.error(res.error);
          return;
        }
        this.notification.success('Tutor eliminado');
        this.router.navigate(['/admin/profesionales']);
      },
      error: () => this.notification.error('No se pudo eliminar el tutor'),
    });
  }

  initials(name?: string | null): string {
    if (!name) return 'T';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return 'T';
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

  onSubmit(): void {
    if (this.form.invalid) return;
    this.errorMessage = '';
    this.activationUrl = null;
    this.submitting = true;
    const v = this.form.getRawValue();

    if (this.isEdit && this.professionalId) {
      this.api
        .updateProfessional(this.professionalId, {
          display_name: v.display_name,
          specialty: v.specialty || undefined,
          institution: v.institution || undefined,
        })
        .subscribe({
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
      return;
    }

    this.api
      .createProfessional({
        email: v.email,
        display_name: v.display_name,
        specialty: v.specialty || undefined,
        institution: v.institution || undefined,
      })
      .subscribe({
        next: (result) => {
          this.submitting = false;
          if ('error' in result) {
            this.errorMessage = result.error;
            return;
          }
          if (result.activation_url) {
            this.activationUrl = result.activation_url;
            this.notification.success('Tutor creado. Copia el enlace de activación para enviárselo.');
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

  copyActivationUrl(): void {
    if (this.activationUrl && typeof navigator?.clipboard?.writeText === 'function') {
      navigator.clipboard.writeText(this.activationUrl);
    }
  }

  goToList(): void {
    this.router.navigate(['/admin/profesionales']);
  }
}
