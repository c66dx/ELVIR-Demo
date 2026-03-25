import { Component, inject, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { EMPTY, forkJoin } from 'rxjs';
import { finalize, switchMap } from 'rxjs/operators';
import { ApiService } from '../../../../core/services/api.service';
import type { JobRole } from '../../../../core/models/job-role.model';
import type { Case } from '../../../../core/models/case.model'; 
 @Component({ 
 selector: 'app-supervised-start',   standalone: true,   imports: [ReactiveFormsModule],   templateUrl: './supervised-start.component.html',   styleUrl: './supervised-start.component.scss',
})
export class SupervisedStartComponent implements OnInit { 
 private fb = inject(FormBuilder); 
 private api = inject(ApiService); 
 private router = inject(Router); 
 private route = inject(ActivatedRoute); 
 form!: FormGroup; 
 jobRoles: JobRole[] = []; 
 cases: Case[] = []; 
 loading = true; 
 submitting = false; 
 errorMessage = ''; 
 searchTerm = ''; 
 selectedCategory: RoleCategory = 'ALL'; 
 readonly roleFilters: RoleCategory[] = ['ALL', 'OPERACIONES', 'ATENCION', 'ADMIN', 'TECNICO', 'OTROS']; 
 private readonly companyContexts: Record<string, { name: string; description: string }> = { 
 operario: { 
 name: 'Logística Andina',   description: 'una empresa dedicada a la distribución y apoyo en bodegas.',   },   'atencion-publico': { 
 name: 'Centro Ciudadano',   description: 'una organización que orienta a personas en servicios y trámites.',   },   administrativo: { 
 name: 'Clínica Horizonte',   description: 'un centro de salud que coordina agenda y documentación interna.',   },   'tecnico-profesional': { 
 name: 'TecnoSoluciones',   description: 'una empresa que implementa soporte y servicios técnicos a clientes.',   },   }; 
 youthId = ''; 
 private step = 1; 
 ngOnInit(): void { 
 this.youthId = this.route.parent?.snapshot.paramMap.get('youthId')  ?? ''; 
 this.form = this.fb.nonNullable.group({ 
 job_role_id: ['', Validators.required],   case_id: ['', Validators.required],   }); 
 forkJoin({ 
 jobRoles: this.api.getJobRoles(),   cases: this.api.getCases(),   }).subscribe({ 
 next: ({ jobRoles, cases }) => { 
 this.jobRoles = jobRoles; 
 this.cases = cases; 
 this.loading = false; 
 },   error: () => (this.loading = false),   }); 
 } 
 hasRole(): boolean { 
 return !!this.form?.get('job_role_id')?.value; 
 } 
 hasCase(): boolean { 
 return !!this.form?.get('case_id')?.value; 
 } 
 currentStep(): number { 
 return this.step; 
 } 
 canContinue(): boolean { 
 if (this.step === 1) return this.hasRole(); 
 if (this.step === 2) return this.hasCase(); 
 return this.form?.valid  ??  false; 
 } 
 goNext(): void { 
 if (!this.canContinue()) return; 
 this.step = Math.min(3, this.step + 1); 
 } 
 goBack(): void { 
 this.step = Math.max(1, this.step - 1); 
 } 
 selectJobRole(role: JobRole): void { 
 if (!this.form) return; 
 this.form.get('job_role_id')?.setValue(String(role.id)); 
 this.form.get('case_id')?.setValue(''); 
 if (this.step > 1) { 
 this.step = 2; 
 } 
 } 
 selectCase(item: Case): void { 
 if (!this.form || !this.hasRole()) return; 
 this.form.get('case_id')?.setValue(String(item.id)); 
 } 
 onSearchChange(event: Event): void { 
 const target = event.target as HTMLInputElement | null; 
 this.searchTerm = target?.value  ?? ''; 
 } 
 setCategory(category: RoleCategory): void { 
 this.selectedCategory = category; 
 } 
 categoryLabel(category: RoleCategory): string { 
 switch (category) { 
 case 'OPERACIONES':   return 'Operaciones'; 
 case 'ATENCION':   return 'Atención'; 
 case 'ADMIN':   return 'Administración'; 
 case 'TECNICO':   return 'Técnico'; 
 case 'OTROS':   return 'Otros'; 
 default:   return 'Todos'; 
 } 
 } 
 roleCategory(role: JobRole): RoleCategory { 
 const slug = (role.slug  ?? '').toLowerCase(); 
 if (slug.includes('operario') || slug.includes('logistica')) return 'OPERACIONES'; 
 if (slug.includes('atencion') || slug.includes('publico')) return 'ATENCION'; 
 if (slug.includes('admin') || slug.includes('administrativo')) return 'ADMIN'; 
 if (slug.includes('tecnico') || slug.includes('técnico') || slug.includes('profesional')) return 'TECNICO'; 
 return 'OTROS'; 
 } 
 filteredRoles(): JobRole[] { 
 const term = this.searchTerm.trim().toLowerCase(); 
 return this.jobRoles.filter((role) => { 
 const matchesTerm = !term || role.name.toLowerCase().includes(term); 
 const category = this.roleCategory(role); 
 const matchesCategory = this.selectedCategory === 'ALL' || this.selectedCategory === category; 
 return matchesTerm && matchesCategory; 
 }); 
 } 
 roleCountLabel(): string { 
 const total = this.jobRoles.length; 
 const visible = this.filteredRoles().length; 
 return total ?  `${visible} de ${total}` : '0 resultados'; 
 } 
 selectedJobRole(): JobRole | null { 
 if (!this.form) return null; 
 const id = this.form.get('job_role_id')?.value; 
 if (!id) return null; 
 return this.jobRoles.find((jr) => String(jr.id) === String(id))  ?? null; 
 } 
 selectedCase(): Case | null { 
 if (!this.form) return null; 
 const id = this.form.get('case_id')?.value; 
 if (!id) return null; 
 return this.cases.find((c) => String(c.id) === String(id))  ?? null; 
 } 
 getCompanyContext(role: JobRole | null): { name: string; description: string } { 
 if (!role) return { name: 'una empresa', description: 'una organización del sector laboral.' }; 
 return this.companyContexts[role.slug]  ??  { 
 name: 'una empresa',   description: 'una organización del sector laboral.',   }; 
 } 
 roleFocus(role: JobRole): string { 
 const slug = role.slug  ?? ''; 
 if (slug.includes('operario')) return 'Operación diaria, orden y cumplimiento de procesos.'; 
 if (slug.includes('atencion') || slug.includes('publico')) return 'Servicio al cliente, comunicación y resolución.'; 
 if (slug.includes('administrativo')) return 'Gestión documental, agenda y coordinación interna.'; 
 if (slug.includes('tecnico')) return 'Diagnóstico, soporte técnico y orientación al cliente.'; 
 return 'Evaluación de experiencia, motivación y habilidades clave.'; 
 } 
 difficultyLabel(difficulty: Case['difficulty']): string { 
 switch (difficulty) { 
 case 'BAJA':   return 'Baja'; 
 case 'MEDIA':   return 'Media'; 
 case 'ALTA':   return 'Alta'; 
 default:   return 'Normal'; 
 } 
 } 
 caseDescription(item: Case): string { 
 switch (item.difficulty) { 
 case 'BAJA':   return 'Entrevista amable, ritmo guiado y preguntas iniciales.'; 
 case 'MEDIA':   return 'Equilibrio entre exigencia y contención; preguntas estándar.'; 
 case 'ALTA':   return 'Entrevista exigente, directa y con mayor presión.'; 
 default:   return 'Escenario estándar para evaluar competencias generales.'; 
 } 
 } 
 caseNarrative(item: Case): string { 
 switch (item.difficulty) { 
 case 'BAJA':   return 'El entrevistador ser cercano y dar tiempo para responder.'; 
 case 'MEDIA':   return 'El tono ser profesional, con foco en experiencia y actitud.'; 
 case 'ALTA':   return 'El entrevistador irá directo al punto y evaluar tu manejo de presión.'; 
 default:   return 'La entrevista seguirá un flujo normal con preguntas de motivación y experiencia.'; 
 } 
 } 
 estimatedDuration(difficulty: Case['difficulty']): string { 
 switch (difficulty) { 
 case 'BAJA':   return '6-8 min'; 
 case 'MEDIA':   return '10-12 min'; 
 case 'ALTA':   return '12-15 min'; 
 default:   return '8-10 min'; 
 } 
 } 
 onSubmit(): void { 
 if (this.form.invalid) return; 
 this.submitting = true; 
 this.errorMessage = ''; 
 const { job_role_id, case_id } = this.form.getRawValue(); 
 this.api   .getSimulationTemplates({ job_role_id, case_id })   .pipe(   switchMap((templates) => { 
 const template = templates[0]; 
 if (!template) { 
 this.errorMessage = 'No se encontr? plantilla para esta combinación'; 
 return EMPTY; 
 } 
 return this.api.getMe().pipe(   switchMap((me) => { 
 const professionalId = me?.role === 'PROFESIONAL' ? me.professional_id : undefined; 
 return this.api.createSession({ 
 youth_id: this.youthId,   simulation_template_id: template.id,   mode: 'SUPERVISADA',   professional_id: professionalId,   }); 
 })   ); 
 }),   finalize(() => (this.submitting = false))   )   .subscribe({ 
 next: (session) => { 
 if (session) { 
 const role = this.selectedJobRole(); 
 const caseItem = this.selectedCase(); 
 this.router.navigate(['/profesional/simulacion', session.id, 'preparacion'], { 
 state: { 
 returnUrl: `/profesional/jovenes/${this.youthId}`,   jobRoleName: role?.name ?? '',   caseName: caseItem?.name  ??  '',   },   }); 
 } 
 },   }); 
 }
} 
 type RoleCategory = 'ALL' | 'OPERACIONES' | 'ATENCION' | 'ADMIN' | 'TECNICO' | 'OTROS';

