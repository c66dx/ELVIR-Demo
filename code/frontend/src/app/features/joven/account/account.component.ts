import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import type { Youth } from '../../../core/models/youth.model';
import { FormActionsComponent } from '../../../shared/form/form-actions/form-actions.component';
import { FormFieldComponent } from '../../../shared/form/form-field/form-field.component';
import { FormGridComponent } from '../../../shared/form/form-grid/form-grid.component';
import { TextInputComponent } from '../../../shared/form/inputs/text-input/text-input.component'; 
 interface MeInfo { 
 user_id: string; 
 role: string; 
 email: string; 
 youth_id?: string; 
 profile_photo_url?: string;
} 
 @Component({ 
 selector: 'app-my-account',   standalone: true,   imports: [   CommonModule,   ReactiveFormsModule,   RouterLink,   FormGridComponent,   FormFieldComponent,   FormActionsComponent,   TextInputComponent,   ],   templateUrl: './account.component.html',   styleUrl: './account.component.scss',
})
export class MyAccountComponent implements OnInit { 
 private api = inject(ApiService); 
 private fb = inject(FormBuilder); 
 me = signal<MeInfo | null>(null); 
 youth = signal<Youth | null>(null); 
 loading = signal(true); 
 photoUrl = signal<string | null>(null); 
 photoError = signal<string | null>(null); 
 photoLoading = signal(false); 
 emailMessage = signal<string | null>(null); 
 emailError = signal<string | null>(null); 
 activationUrl = signal<string | null>(null); 
 emailForm = this.fb.group({ 
 new_email: ['', [Validators.required, Validators.email]],   current_password: ['', [Validators.required]],   }); 
 initials = computed(() => { 
 const name = this.youth()?.display_name || this.me()?.email || 'U'; 
 const parts = name.trim().split(/\s+/); 
 const letters = parts.slice(0, 2).map((p) => p[0]?.toUpperCase()  ?? ''); 
 return letters.join('') || 'U'; 
 }); 
 ngOnInit(): void { 
 this.api.getMe().subscribe((me) => { 
 this.me.set(me as MeInfo | null); 
 this.photoUrl.set(me?.profile_photo_url  ?? null); 
 if (me?.youth_id) { 
 this.api.getYouth(me.youth_id).subscribe((y) => { 
 this.youth.set(y); 
 if (y?.profile_photo_url) { 
 this.photoUrl.set(y.profile_photo_url); 
 } 
 }); 
 } 
 this.loading.set(false); 
 }); 
 } 
 onPhotoSelected(event: Event): void { 
 const input = event.target as HTMLInputElement; 
 const file = input.files?.[0]; 
 if (!file) return; 
 this.photoError.set(null); 
 this.photoLoading.set(true); 
 const youthId = this.me()?.youth_id; 
 if (youthId) { 
 this.api.uploadYouthPhoto(youthId, file).subscribe((res) => { 
 this.photoLoading.set(false); 
 if ('error' in res) { 
 this.photoError.set(res.error); 
 return; 
 } 
 this.youth.set(res); 
 this.photoUrl.set(res.profile_photo_url  ?? null); 
 }); 
 } else { 
 this.api.uploadProfilePhoto(file).subscribe((res) => { 
 this.photoLoading.set(false); 
 if ('error' in res) { 
 this.photoError.set(res.error); 
 return; 
 } 
 this.photoUrl.set(res.url); 
 }); 
 } 
 input.value = ''; 
 } 
 onChangeEmail(): void { 
 if (this.emailForm.invalid) return; 
 this.emailError.set(null); 
 this.emailMessage.set(null); 
 this.activationUrl.set(null); 
 const { new_email, current_password } = this.emailForm.value; 
 if (!new_email || !current_password) return; 
 this.api.requestEmailChange(new_email, current_password).subscribe((res) => { 
 if ('error' in res) { 
 this.emailError.set(res.error); 
 return; 
 } 
 this.emailMessage.set('Se generó un enlace de confirmación para cambiar tu correo.'); 
 if (res.activation_url) { 
 this.activationUrl.set(res.activation_url); 
 } 
 this.emailForm.reset(); 
 }); 
 }
}
