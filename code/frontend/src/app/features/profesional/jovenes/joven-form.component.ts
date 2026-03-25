import { Component, inject, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AbstractControl, FormBuilder, FormGroup, ReactiveFormsModule, ValidationErrors, ValidatorFn, Validators } from '@angular/forms';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';
import { NotificationService } from '../../../core/services/notification.service';
import { PROFILE_CHECKLIST_ITEMS } from '../../../core/models/youth.model';
import { extractErrorMessage } from '../../../core/utils/http-error.util';
import { FormContainerComponent } from '../../../shared/form/form-container/form-container.component';
import { FormSectionComponent } from '../../../shared/form/form-section/form-section.component';
import { FormGridComponent } from '../../../shared/form/form-grid/form-grid.component';
import { FormFieldComponent } from '../../../shared/form/form-field/form-field.component';
import { FormActionsComponent } from '../../../shared/form/form-actions/form-actions.component';
import { TextInputComponent } from '../../../shared/form/inputs/text-input/text-input.component';
import { TextareaInputComponent } from '../../../shared/form/inputs/textarea-input/textarea-input.component';
import { ToggleInputComponent } from '../../../shared/form/inputs/toggle-input/toggle-input.component';
import { CheckboxGroupComponent } from '../../../shared/form/inputs/checkbox-group/checkbox-group.component'; 
 function normalizeRut(value: string): string { 
 return value.replace(/[^0-9kK]/g, '').toUpperCase();
} 
 function computeRutDv(body: string): string { 
 let sum = 0; 
 let multiplier = 2; 
 for (let i = body.length - 1; i >= 0; i -= 1) { 
 sum += Number(body[i]) * multiplier; 
 multiplier = multiplier === 7 ? 2 : multiplier + 1; 
 } 
 const mod = 11 - (sum % 11); 
 if (mod === 11) return '0'; 
 if (mod === 10) return 'K'; 
 return String(mod);
} 
 function formatRut(value: string): string { 
 const cleaned = normalizeRut(value); 
 if (cleaned.length < 2) return value.trim(); 
 const body = cleaned.slice(0, -1); 
 const dv = cleaned.slice(-1); 
 const withDots = body.replace(/\B(?=(\d{3})+(?!\d))/g, '.'); 
 return `${withDots}-${dv}`;
} 
 const rutValidator: ValidatorFn = (control: AbstractControl): ValidationErrors | null => { 
 const raw = String(control.value  ?? '').trim(); 
 if (!raw) return null; 
 const cleaned = normalizeRut(raw); 
 if (cleaned.length < 2) return { rut: true }; 
 if (!/^\d+[0-9K]$/.test(cleaned)) return { rut: true }; 
 const body = cleaned.slice(0, -1); 
 if (!body) return { rut: true }; 
 const dv = cleaned.slice(-1); 
 return computeRutDv(body) === dv ? null : { rut: true };
}; 
 /** Formulario crear/editar joven. Checklist perfil, login_enabled, email. Genera activation_url si aplica. */
@Component({ 
 selector: 'app-joven-form',   standalone: true,   imports: [   ReactiveFormsModule,   FormsModule,   RouterLink,   FormContainerComponent,   FormSectionComponent,   FormGridComponent,   FormFieldComponent,   FormActionsComponent,   TextInputComponent,   TextareaInputComponent,   ToggleInputComponent,   CheckboxGroupComponent,   ],   templateUrl: './joven-form.component.html',   styleUrl: './joven-form.component.scss',
})
export class JovenFormComponent implements OnInit { 
 private fb = inject(FormBuilder); 
 private api = inject(ApiService); 
 private router = inject(Router); 
 private route = inject(ActivatedRoute); 
 private notification = inject(NotificationService); 
 readonly checklistItems = PROFILE_CHECKLIST_ITEMS; 
 form: FormGroup = this.fb.nonNullable.group({ 
 display_name: ['', Validators.required],   rut: ['', rutValidator],   phone: [''],   year_of_birth: [null as number | null],   diagnosis: [''],   login_enabled: [true],   email: [''],   general_notes: [''],   profile_checklist: [[] as string[]],   }); 
 youthId: string | null = null; 
 isEdit = false; 
 submitting = false; 
 errorMessage = ''; 
 currentYear = new Date().getFullYear(); 
 /** Tras crear/editar con login habilitado (sin cuenta activa), se muestra el enlace de activación. */   activationUrl: string | null = null; 
 /** Si el joven tiene login_enabled pero no user_id, necesita invitación (crear o reenviar). */   needsInvitation = false; 
 /** Si el joven ya tiene cuenta activa (user_id). En edit, si no tiene, al habilitar login pedimos email. */   hasUserAccount = false; 
 /** Datos del joven cargado (para mostrar identifier y email en modo solo lectura). */   currentYouth: { identifier?: string; email?: string } | null = null; 
 photoUrl: string | null = null; 
 photoPreviewUrl: string | null = null; 
 pendingPhotoFile: File | null = null; 
 photoUploading = false; 
 photoError = ''; 
 private readonly maxPhotoBytes = 5 * 1024 * 1024; 
 /** Modal cambiar email */   showChangeEmailModal = false; 
 newEmailForChange = ''; 
 changingEmail = false; 
 changeEmailError = ''; 
 ngOnInit(): void { 
 this.youthId = this.route.parent?.snapshot.paramMap.get('youthId')  ?? null; 
 this.isEdit = !!this.youthId; 
 this.form.get('rut')?.valueChanges.subscribe(() => this.clearRutServerError()); 
 this.form.get('email')?.valueChanges.subscribe(() => this.clearEmailServerError()); 
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
 this.currentYouth = { identifier: youth.identifier, email: youth.email }; 
 this.photoUrl = youth.profile_photo_url  ?? null; 
 this.form.patchValue({ 
 display_name: youth.display_name,   rut: youth.rut ?  formatRut(youth.rut) : '',   phone: youth.phone ?? '',   year_of_birth: youth.year_of_birth ?? null,   diagnosis: youth.diagnosis ?? '',   login_enabled: youth.login_enabled,   general_notes: youth.general_notes ?? '',   profile_checklist: youth.profile_checklist  ??  [],   }); 
 const emailCtrl = this.form.get('email'); 
 if (this.needsInvitation && emailCtrl) { 
 emailCtrl.setValidators([Validators.required, Validators.email]); 
 } 
 if (!youth.login_enabled && emailCtrl) { 
 emailCtrl.clearValidators(); 
 } 
 if (this.needsInvitation && youth.email) { 
 emailCtrl?.setValue(youth.email); 
 } 
 } 
 },   }); 
 } else { 
 this.currentYouth = null; 
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
 const rutRaw = String(value.rut  ?? '').trim(); 
 const rutValue = rutRaw ?  formatRut(rutRaw) : undefined; 
 const shouldSendEmail = value.login_enabled && (!this.isEdit || !this.hasUserAccount); 
 const emailValue = shouldSendEmail && value.email ? value.email : undefined; 
 if (this.isEdit && this.youthId) { 
 this.api   .updateYouth(this.youthId, { 
 display_name: value.display_name,   rut: rutValue,   phone: value.phone || undefined,   year_of_birth: value.year_of_birth ?? undefined,   diagnosis: value.diagnosis || undefined,   login_enabled: value.login_enabled,   email: emailValue,   general_notes: value.general_notes || undefined,   profile_checklist: value.profile_checklist?.length ? value.profile_checklist : undefined,   })   .subscribe({ 
 next: (res) => { 
 if (res === null) { 
 this.errorMessage = 'Error al actualizar. Verifica los datos e intenta de nuevo.'; 
 this.submitting = false; 
 return; 
 } 
 if (this.pendingPhotoFile) { 
 this.uploadYouthPhoto(this.youthId, this.pendingPhotoFile); 
 } 
 if (res.activation_url) { 
 this.activationUrl = res.activation_url; 
 this.submitting = false; 
 this.notification.success('Joven actualizado. Copia el enlace de activación.'); 
 } else { 
 this.notification.success('Joven actualizado correctamente'); 
 this.router.navigate(['/profesional/jovenes']); 
 } 
 },   error: (err) => { 
 this.applyRutBackendError(err); 
 this.applyEmailBackendError(err); 
 const requestId = err?.headers?.get?.('X-Request-ID')  ?? null; 
 this.errorMessage = extractErrorMessage(err, requestId); 
 this.submitting = false; 
 },   }); 
 } else { 
 this.api   .createYouth({ 
 display_name: value.display_name,   rut: rutValue,   phone: value.phone || undefined,   year_of_birth: value.year_of_birth ?? undefined,   diagnosis: value.diagnosis || undefined,   login_enabled: value.login_enabled,   email: emailValue,   general_notes: value.general_notes || undefined,   profile_checklist: value.profile_checklist?.length ? value.profile_checklist : undefined,   is_active: true,   })   .subscribe({ 
 next: (res) => { 
 if (this.pendingPhotoFile) { 
 this.uploadYouthPhoto(res.id, this.pendingPhotoFile); 
 } 
 if (res.activation_url) { 
 this.activationUrl = res.activation_url; 
 this.submitting = false; 
 this.notification.success('Joven creado. Copia el enlace de activación para enviárselo.'); 
 } else { 
 this.notification.success('Joven creado correctamente'); 
 this.router.navigate(['/profesional/jovenes']); 
 } 
 },   error: (err) => { 
 this.applyRutBackendError(err); 
 this.applyEmailBackendError(err); 
 const requestId = err?.headers?.get?.('X-Request-ID')  ?? null; 
 this.errorMessage = extractErrorMessage(err, requestId); 
 this.submitting = false; 
 },   }); 
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
 photoSrc(): string | null { 
 return this.photoPreviewUrl || this.photoUrl; 
 } 
 photoInitials(): string { 
 const name = String(this.form.get('display_name')?.value || '').trim(); 
 if (!name) return 'J'; 
 const parts = name.split(/\s+/).filter(Boolean); 
 const first = parts[0]?.[0]  ?? ''; 
 const second = parts.length > 1 ?  (parts[1]?.[0]  ??  '') : ''; 
 return (first + second).toUpperCase() || 'J'; 
 } 
 onPhotoSelected(event: Event): void { 
 const input = event.target as HTMLInputElement | null; 
 const file = input?.files?.[0]; 
 if (!file) return; 
 if (input) input.value = ''; 
 const allowedTypes = ['image/png', 'image/jpeg', 'image/webp']; 
 const extensionOk = /\.(png|jpe?g|webp)$/i.test(file.name); 
 if (!allowedTypes.includes(file.type) && !extensionOk) { 
 this.photoError = 'Formato no permitido. Usa JPG, PNG o WebP.'; 
 return; 
 } 
 if (file.size > this.maxPhotoBytes) { 
 this.photoError = 'Imagen demasiado grande. Máximo 5 MB.'; 
 return; 
 } 
 this.photoError = ''; 
 this.pendingPhotoFile = file; 
 this.setPhotoPreview(file); 
 if (this.isEdit && this.youthId) { 
 this.uploadYouthPhoto(this.youthId, file); 
 } 
 } 
 private setPhotoPreview(file: File): void { 
 if (this.photoPreviewUrl && this.photoPreviewUrl.startsWith('blob:')) { 
 URL.revokeObjectURL(this.photoPreviewUrl); 
 } 
 this.photoPreviewUrl = URL.createObjectURL(file); 
 } 
 private uploadYouthPhoto(youthId: string | null, file: File): void { 
 if (!youthId) return; 
 this.photoUploading = true; 
 this.api.uploadYouthPhoto(youthId, file).subscribe({ 
 next: (res) => { 
 this.photoUploading = false; 
 if ('error' in res) { 
 this.photoError = res.error; 
 return; 
 } 
 this.photoUrl = res.profile_photo_url  ??  this.photoUrl; 
 if (this.photoPreviewUrl && this.photoPreviewUrl.startsWith('blob:')) { 
 URL.revokeObjectURL(this.photoPreviewUrl); 
 } 
 this.photoPreviewUrl = null; 
 this.pendingPhotoFile = null; 
 },   error: () => { 
 this.photoUploading = false; 
 this.photoError = 'Error al subir la foto.'; 
 },   }); 
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
 onRutBlur(): void { 
 const ctrl = this.form.get('rut'); 
 if (!ctrl) return; 
 const value = String(ctrl.value  ?? '').trim(); 
 if (!value) return; 
 ctrl.setValue(formatRut(value), { emitEvent: false }); 
 ctrl.updateValueAndValidity({ emitEvent: false }); 
 } 
 private applyRutBackendError(err: unknown): void { 
 const detail = (err as { error?: { detail?: unknown } })?.error?.detail; 
 const msg = typeof detail === 'string' ? detail : ''; 
 if (!msg || !msg.toLowerCase().includes('rut')) return; 
 this.setRutServerError(msg); 
 } 
 private applyEmailBackendError(err: unknown): void { 
 const detail = (err as { error?: { detail?: unknown } })?.error?.detail; 
 if (!detail) return; 
 if (typeof detail === 'string') { 
 const msg = detail.toLowerCase(); 
 if (msg.includes('email')) { 
 this.setEmailServerError(detail); 
 } 
 return; 
 } 
 if (Array.isArray(detail)) { 
 const emailError = detail.find((item) => { 
 const loc = item?.loc  ?? []; 
 return Array.isArray(loc) && loc.includes('email'); 
 }); 
 const msg = emailError?.msg  ??  emailError?.message; 
 if (msg) { 
 this.setEmailServerError(String(msg)); 
 } 
 } 
 } 
 private setRutServerError(message: string): void { 
 const ctrl = this.form.get('rut'); 
 if (!ctrl) return; 
 const errors = { ...(ctrl.errors  ??  {}), server: message }; 
 ctrl.setErrors(errors); 
 } 
 private setEmailServerError(message: string): void { 
 const ctrl = this.form.get('email'); 
 if (!ctrl) return; 
 const errors = { ...(ctrl.errors  ??  {}), server: message }; 
 ctrl.setErrors(errors); 
 } 
 private clearRutServerError(): void { 
 const ctrl = this.form.get('rut'); 
 if (!ctrl?.errors?.['server']) return; 
 const { server, ...rest } = ctrl.errors as Record<string, unknown>; 
 ctrl.setErrors(Object.keys(rest).length ? rest : null); 
 } 
 private clearEmailServerError(): void { 
 const ctrl = this.form.get('email'); 
 if (!ctrl?.errors?.['server']) return; 
 const { server, ...rest } = ctrl.errors as Record<string, unknown>; 
 ctrl.setErrors(Object.keys(rest).length ? rest : null); 
 } 
 openChangeEmailModal(): void { 
 this.newEmailForChange = this.currentYouth?.email  ?? ''; 
 this.changeEmailError = ''; 
 this.showChangeEmailModal = true; 
 } 
 closeChangeEmailModal(): void { 
 this.showChangeEmailModal = false; 
 this.newEmailForChange = ''; 
 this.changeEmailError = ''; 
 } 
 submitChangeEmail(): void { 
 const email = this.newEmailForChange.trim(); 
 this.changeEmailError = ''; 
 if (!email || !this.youthId) return; 
 const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/; 
 if (!emailRegex.test(email)) { 
 this.changeEmailError = 'Ingresa un email válido'; 
 this.notification.error(this.changeEmailError); 
 return; 
 } 
 this.changingEmail = true; 
 this.api.changeYouthEmail(this.youthId, email).subscribe({ 
 next: (res) => { 
 this.changingEmail = false; 
 if (res === null) { 
 this.changeEmailError = 'Error al cambiar el email'; 
 this.notification.error(this.changeEmailError); 
 return; 
 } 
 this.currentYouth = { ...this.currentYouth, email: res.email  ??  email }; 
 this.closeChangeEmailModal(); 
 if (res.activation_url) { 
 this.activationUrl = res.activation_url; 
 this.notification.success('Email actualizado. Entrega el nuevo enlace al joven.'); 
 } else { 
 this.notification.success('Email actualizado correctamente'); 
 } 
 },   error: (err) => { 
 this.changingEmail = false; 
 const msg = err.error?.detail  ?? 'Error al cambiar el email'; 
 this.changeEmailError = typeof msg === 'string' ? msg : 'Error al cambiar el email'; 
 this.notification.error(this.changeEmailError); 
 },   }); 
 }
}

