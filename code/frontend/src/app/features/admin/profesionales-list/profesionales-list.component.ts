import { Component, inject, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { NotificationService } from '../../../core/services/notification.service'; 
 /** Lista de profesionales (Admin). */
@Component({ 
 selector: 'app-profesionales-list',   standalone: true,   imports: [RouterLink],   templateUrl: './profesionales-list.component.html',   styleUrl: './profesionales-list.component.scss',
})
export class ProfesionalesListComponent implements OnInit { 
 private api = inject(ApiService); 
 private notification = inject(NotificationService); 
 professionals: { id: string; display_name: string; specialty?: string; institution?: string; is_active: boolean; profile_photo_url?: string }[] = []; 
 loading = true; 
 page = 1; 
 total = 0; 
 readonly pageSize = 20; 
 ngOnInit(): void { 
 this.loadPage(1); 
 } 
 loadPage(page: number): void { 
 this.loading = true; 
 this.api.getProfessionalsPaged({ page, page_size: this.pageSize }).subscribe({ 
 next: (list) => { 
 this.professionals = list.items; 
 this.total = list.total; 
 this.page = list.page; 
 this.loading = false; 
 },   error: () => { 
 this.loading = false; 
 },   }); 
 } 
 totalPages(): number { 
 return Math.max(1, Math.ceil(this.total / this.pageSize)); 
 } 
 prevPage(): void { 
 if (this.page > 1) { 
 this.loadPage(this.page - 1); 
 } 
 } 
 nextPage(): void { 
 if (this.page < this.totalPages()) { 
 this.loadPage(this.page + 1); 
 } 
 } 
 onDeactivate(professional: { id: string; display_name: string; specialty?: string; institution?: string }): void { 
 if (!confirm(`Desactivar a ${professional.display_name}?`)) return; 
 this.api   .updateProfessional(professional.id, { 
 display_name: professional.display_name,   specialty: professional.specialty,   institution: professional.institution,   is_active: false,   })   .subscribe({ 
 next: (res) => { 
 if ('error' in res) { 
 this.notification.error(res.error); 
 return; 
 } 
 this.notification.success('Tutor desactivado'); 
 this.loadPage(this.page); 
 },   error: () => this.notification.error('No se pudo desactivar el tutor'),   }); 
 } 
 onActivate(professional: { id: string; display_name: string; specialty?: string; institution?: string }): void { 
 if (!confirm(`Reactivar a ${professional.display_name}?`)) return; 
 this.api   .updateProfessional(professional.id, { 
 display_name: professional.display_name,   specialty: professional.specialty,   institution: professional.institution,   is_active: true,   })   .subscribe({ 
 next: (res) => { 
 if ('error' in res) { 
 this.notification.error(res.error); 
 return; 
 } 
 this.notification.success('Tutor reactivado'); 
 this.loadPage(this.page); 
 },   error: () => this.notification.error('No se pudo reactivar el tutor'),   }); 
 } 
 onDelete(professional: { id: string; display_name: string }): void { 
 if (!confirm(`Eliminar a ${professional.display_name}? Esta acción no se puede deshacer.`)) return; 
 this.api.deleteProfessionalAsAdmin(professional.id).subscribe({ 
 next: (res) => { 
 if ('error' in res) { 
 this.notification.error(res.error); 
 return; 
 } 
 this.notification.success('Tutor eliminado'); 
 this.loadPage(this.page); 
 },   error: () => this.notification.error('No se pudo eliminar el tutor'),   }); 
 } 
 initials(name?: string | null): string { 
 if (!name) return 'T'; 
 const parts = name.trim().split(/\s+/).filter(Boolean); 
 if (parts.length === 0) return 'T'; 
 if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase(); 
 return (parts[0][0] + parts[1][0]).toUpperCase(); 
 }
}
