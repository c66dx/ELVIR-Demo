import { Component, inject, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';
import { NotificationService } from '../../../core/services/notification.service';
import { PROFILE_CHECKLIST_ITEMS } from '../../../core/models/youth.model';

/** Formulario crear/editar joven. Checklist perfil, login_enabled, email. Genera activation_url si aplica. */
@Component({
  selector: 'app-joven-form',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './joven-form.component.html',
  styleUrl: './joven-form.component.scss',
})
export class JovenFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private api = inject(ApiService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private notification = inject(NotificationService);

  readonly checklistItems = PROFILE_CHECKLIST_ITEMS;

  form: FormGroup = this.fb.nonNullable.group({
    display_name: ['', Validators.required],
    identifier: [''],
    phone: [''],
    year_of_birth: [null as number | null],
    diagnosis: [''],
    login_enabled: [true],
    email: [''],
    general_notes: [''],
    profile_checklist: [[] as string[]],
  });

  youthId: string | null = null;
  isEdit = false;
  submitting = false;
  errorMessage = '';
  currentYear = new Date().getFullYear();
  /** Tras crear/editar con login habilitado (sin cuenta activa), se muestra el enlace de activación. */
  activationUrl: string | null = null;
  /** Si el joven tiene login_enabled pero no user_id, necesita invitación (crear o reenviar). */
  needsInvitation = false;
  /** Si el joven ya tiene cuenta activa (user_id). En edit, si no tiene, al habilitar login pedimos email. */
  hasUserAccount = false;

  ngOnInit(): void {
    this.youthId = this.route.parent?.snapshot.paramMap.get('youthId') ?? null;
    this.isEdit = !!this.youthId;

    this.form.get('login_enabled')?.valueChanges.subscribe((enabled) => {
      const emailCtrl = this.form.get('email');
      if (!emailCtrl) return;
      const requireEmail = enabled && (!this.isEdit || !this.hasUserAccount);
      if (requireEmail) {
        emailCtrl.setValidators([Validators.required, Validators.email]);
      } else {
        emailCtrl.clearValidators();
        emailCtrl.setValue('');
      }
      emailCtrl.updateValueAndValidity();
    });

    if (this.isEdit && this.youthId) {
      this.api.getYouth(this.youthId).subscribe({
        next: (youth) => {
          if (youth) {
            this.hasUserAccount = !!youth.user_id;
            this.needsInvitation = youth.login_enabled && !youth.user_id;
            this.form.patchValue({
              display_name: youth.display_name,
              identifier: youth.identifier ?? '',
              phone: youth.phone ?? '',
              year_of_birth: youth.year_of_birth ?? null,
              diagnosis: youth.diagnosis ?? '',
              login_enabled: youth.login_enabled,
              general_notes: youth.general_notes ?? '',
              profile_checklist: youth.profile_checklist ?? [],
            });
            const emailCtrl = this.form.get('email');
            if (this.needsInvitation && emailCtrl) {
              emailCtrl.setValidators([Validators.required, Validators.email]);
            }
            if (!youth.login_enabled && emailCtrl) {
              emailCtrl.clearValidators();
            }
          }
        },
      });
    } else {
      const emailCtrl = this.form.get('email');
      if (this.form.get('login_enabled')?.value && emailCtrl) {
        emailCtrl.setValidators([Validators.required, Validators.email]);
      }
    }
  }

  onSubmit(): void {
    if (this.form.invalid) return;

    this.submitting = true;
    this.errorMessage = '';
    this.activationUrl = null;
    const value = this.form.getRawValue();

    if (this.isEdit && this.youthId) {
      this.api
        .updateYouth(this.youthId, {
          display_name: value.display_name,
          identifier: value.identifier || undefined,
          phone: value.phone || undefined,
          year_of_birth: value.year_of_birth ?? undefined,
          diagnosis: value.diagnosis || undefined,
          login_enabled: value.login_enabled,
          email: value.login_enabled ? value.email : undefined,
          general_notes: value.general_notes || undefined,
          profile_checklist: value.profile_checklist?.length ? value.profile_checklist : undefined,
        })
        .subscribe({
          next: (res) => {
            if (res?.activation_url) {
              this.activationUrl = res.activation_url;
              this.submitting = false;
              this.notification.success('Joven actualizado. Copia el enlace de activación.');
            } else {
              this.notification.success('Joven actualizado correctamente');
              this.router.navigate(['/profesional/jovenes']);
            }
          },
          error: () => {
            this.errorMessage = 'Error al actualizar';
            this.submitting = false;
          },
        });
    } else {
      this.api
        .createYouth({
          display_name: value.display_name,
          identifier: value.identifier || undefined,
          phone: value.phone || undefined,
          year_of_birth: value.year_of_birth ?? undefined,
          diagnosis: value.diagnosis || undefined,
          login_enabled: value.login_enabled,
          email: value.login_enabled ? value.email : undefined,
          general_notes: value.general_notes || undefined,
          profile_checklist: value.profile_checklist?.length ? value.profile_checklist : undefined,
          is_active: true,
        })
        .subscribe({
          next: (res) => {
            if (res.activation_url) {
              this.activationUrl = res.activation_url;
              this.submitting = false;
              this.notification.success('Joven creado. Copia el enlace de activación para enviárselo.');
            } else {
              this.notification.success('Joven creado correctamente');
              this.router.navigate(['/profesional/jovenes']);
            }
          },
          error: () => {
            this.errorMessage = 'Error al crear el joven';
            this.submitting = false;
          },
        });
    }
  }

  copyActivationUrl(): void {
    if (this.activationUrl && typeof navigator?.clipboard?.writeText === 'function') {
      navigator.clipboard.writeText(this.activationUrl);
    }
  }

  goToList(): void {
    this.router.navigate(['/profesional/jovenes']);
  }

  isChecklistSelected(slug: string): boolean {
    const arr = this.form.get('profile_checklist')?.value as string[];
    return Array.isArray(arr) && arr.includes(slug);
  }

  toggleChecklist(slug: string): void {
    const ctrl = this.form.get('profile_checklist');
    if (!ctrl) return;
    const arr = [...(ctrl.value as string[])];
    const idx = arr.indexOf(slug);
    if (idx >= 0) arr.splice(idx, 1);
    else arr.push(slug);
    ctrl.setValue(arr);
  }
}
