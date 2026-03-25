import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';
import { FormFieldComponent } from '../../../shared/form/form-field/form-field.component';
import { TextInputComponent } from '../../../shared/form/inputs/text-input/text-input.component'; 
 type ActivateState = 'loading' | 'valid' | 'invalid' | 'success' | 'error'; 
 @Component({ 
 selector: 'app-activate',   standalone: true,   imports: [ReactiveFormsModule, RouterLink, FormFieldComponent, TextInputComponent],   templateUrl: './activate.component.html',   styleUrl: './activate.component.scss',
})
export class ActivateComponent implements OnInit { 
 private fb = inject(FormBuilder); 
 private api = inject(ApiService); 
 private router = inject(Router); 
 private route = inject(ActivatedRoute); 
 state = signal<ActivateState>('loading'); 
 email = signal<string>(''); 
 displayName = signal<string>(''); 
 isChangeEmail = signal<boolean>(false); 
 errorCode = signal<string | null>(null); 
 form: FormGroup = this.fb.nonNullable.group({ 
 currentPassword: [''],   password: [''],   passwordConfirm: [''],   }); 
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
 this.displayName.set(res.display_name  ?? ''); 
 this.isChangeEmail.set(res.is_change_email  ??  false); 
 this.setupFormValidators(res.is_change_email  ??  false); 
 this.state.set('valid'); 
 } else { 
 this.state.set('invalid'); 
 this.errorCode.set(res.error  ?? 'TOKEN_NOT_FOUND'); 
 } 
 },   error: () => { 
 this.state.set('invalid'); 
 this.errorCode.set('TOKEN_NOT_FOUND'); 
 },   }); 
 } 
 private setupFormValidators(isChangeEmail: boolean): void { 
 const currentCtrl = this.form.get('currentPassword'); 
 const passwordCtrl = this.form.get('password'); 
 const confirmCtrl = this.form.get('passwordConfirm'); 
 if (!currentCtrl || !passwordCtrl || !confirmCtrl) return; 
 if (isChangeEmail) { 
 currentCtrl.setValidators([Validators.required]); 
 passwordCtrl.clearValidators(); 
 passwordCtrl.setValue(''); 
 confirmCtrl.clearValidators(); 
 confirmCtrl.setValue(''); 
 } else { 
 currentCtrl.clearValidators(); 
 currentCtrl.setValue(''); 
 passwordCtrl.setValidators([Validators.required, Validators.minLength(6)]); 
 confirmCtrl.setValidators([Validators.required]); 
 } 
 currentCtrl.updateValueAndValidity(); 
 passwordCtrl.updateValueAndValidity(); 
 confirmCtrl.updateValueAndValidity(); 
 } 
 onSubmit(): void { 
 const { currentPassword, password, passwordConfirm } = this.form.getRawValue(); 
 const changeEmail = this.isChangeEmail(); 
 if (changeEmail) { 
 if (!currentPassword?.trim()) { 
 this.form.get('currentPassword')?.setErrors({ required: true }); 
 return; 
 } 
 if (password?.trim() && password !== passwordConfirm) { 
 this.form.get('passwordConfirm')?.setErrors({ mismatch: true }); 
 return; 
 } 
 if (password?.trim() && password.length < 6) { 
 this.form.get('password')?.setErrors({ minlength: { requiredLength: 6 } }); 
 return; 
 } 
 } else { 
 if (password !== passwordConfirm) { 
 this.form.get('passwordConfirm')?.setErrors({ mismatch: true }); 
 return; 
 } 
 } 
 if (!this.token) return; 
 const params: { token: string; password?: string; current_password?: string } = { token: this.token }; 
 if (changeEmail) { 
 params.current_password = currentPassword; 
 if (password?.trim()) params.password = password; 
 } else { 
 params.password = password; 
 } 
 this.api.activateAccount(params).subscribe({ 
 next: (res) => { 
 if (res.success) { 
 this.state.set('success'); 
 } else { 
 this.state.set('error'); 
 this.errorCode.set(res.error  ?? null); 
 } 
 },   error: () => { 
 this.state.set('error'); 
 this.errorCode.set('TOKEN_NOT_FOUND'); 
 },   }); 
 } 
 goToLogin(): void { 
 this.router.navigate(['/login']); 
 }
}
