import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { MaterialApiService } from '@core/services/material-api.service';
import { AuthService } from '@core/services/auth.service';
import type { SupportMaterial } from '@core/models/support-material.model';
import type { MaterialType } from '@core/models/types.model';
import { formatDate } from '@shared/utils/date-format.util'; 
 @Component({ 
 selector: 'app-material-list',   standalone: true,   imports: [AsyncPipe, RouterLink],   templateUrl: './material-list.component.html',   styleUrl: './material-list.component.scss',
 changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MaterialListComponent { 
 private materials = inject(MaterialApiService); 
 private auth = inject(AuthService); 
 private page$ = new BehaviorSubject(1); 
 readonly pageSize = 10; 
 readonly formatDate = formatDate; 
 materials$ = this.page$.pipe(   switchMap((page) => this.materials.getSupportMaterialPaged({ page, page_size: this.pageSize }))   ); 
 get createLink(): string { 
 return this.auth.getRole() === 'ADMIN' ? '/admin/material/nuevo' : '/profesional/material/nuevo'; 
 } 
 openMaterial(url: string): void { 
 window.open(url, '_blank'); 
 } 
 totalPages(total: number, pageSize: number): number { 
 if (!pageSize) return 1; 
 return Math.max(1, Math.ceil(total / pageSize)); 
 } 
 prevPage(current: number): void { 
 if (current > 1) this.page$.next(current - 1); 
 } 
 nextPage(current: number, total: number, pageSize: number): void { 
 if (current < this.totalPages(total, pageSize)) this.page$.next(current + 1); 
 } 
 typeLabel(type: MaterialType): string { 
 switch (type) { 
 case 'VIDEO':   return 'Video'; 
 case 'PDF':   return 'Guía PDF'; 
 default:   return 'Enlace'; 
 } 
 } 
 typeAbbr(type: MaterialType): string { 
 switch (type) { 
 case 'VIDEO':   return 'VID'; 
 case 'PDF':   return 'PDF'; 
 default:   return 'WEB'; 
 } 
 } 
 materialSummary(material: SupportMaterial): string { 
 const desc = material.description?.trim(); 
 if (desc) { 
 return desc.length > 140 ? `${desc.slice(0, 137)}...` : desc; 
 } 
 if (material.type === 'VIDEO') { 
 return 'Guía audiovisual para reforzar habilidades clave de entrevista.'; 
 } 
 if (material.type === 'PDF') { 
 return 'Resumen descargable con recomendaciones y ejemplos prácticos.'; 
 } 
 return 'Recurso externo con consejos aplicables a entrevistas laborales.'; 
 }
}


