import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { of, BehaviorSubject, combineLatest } from 'rxjs';
import { switchMap, map } from 'rxjs/operators';
import { YouthService } from '@core/services/youth.service';
import { MaterialApiService } from '@core/services/material-api.service';
import type { MaterialSuggestion } from '@core/models/material-suggestion.model';
import type { SupportMaterial } from '@core/models/support-material.model';
import type { MaterialType } from '@core/models/types.model'; 
 interface SuggestionWithMaterial extends MaterialSuggestion { 
 material?: SupportMaterial;
} 
/**   * Material de apoyo: sección "Sugerido para ti" (por profesional) y "Catálogo".   * Registra vistas al abrir material para marcar como visto.   */
@Component({ 
 selector: 'app-material-joven',   standalone: true,   imports: [AsyncPipe],   templateUrl: './material-joven.component.html',   styleUrl: './material-joven.component.scss',
 changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MaterialJovenComponent { 
 private youthService = inject(YouthService); 
 private materials = inject(MaterialApiService); 
 viewedMaterialIds = signal<Set<string>>(new Set()); 
 private suggestedPage$ = new BehaviorSubject(1); 
 private catalogPage$ = new BehaviorSubject(1); 
 readonly suggestedPageSize = 6; 
 readonly catalogPageSize = 8; 
 private currentYouthId: string | null = null; 
 suggested$ = combineLatest([this.youthService.getCurrentYouthId(), this.suggestedPage$]).pipe(
   switchMap(([youthId, page]) => {
     this.currentYouthId = youthId;
     return youthId
       ? this.materials.getYouthMaterialSuggestionsPaged(youthId, { page, page_size: this.suggestedPageSize }).pipe(
           map((paged) => ({
             ...paged,
             items: paged.items.map((s) => ({
               ...s,
               material: (s as SuggestionWithMaterial).material ?? undefined,
             })),
           }))
         )
       : of({ items: [], total: 0, page: 1, page_size: this.suggestedPageSize });
   })
 );
 catalog$ = this.catalogPage$.pipe(   switchMap((page) =>   this.materials.getSupportMaterialPaged({ page, page_size: this.catalogPageSize }).pipe(   map((paged) => ({ ...paged }))   )   )   ); 
 constructor() { 
 this.youthService.getCurrentYouthId().subscribe((youthId) => { 
 this.currentYouthId = youthId; 
 if (youthId) { 
 this.materials.getYouthMaterialViewsPaged(youthId, { page: 1, page_size: 200 }).subscribe({ 
 next: (views) => { 
 this.viewedMaterialIds.update((set) => new Set([...set, ...views.items.map((v) => v.material_id)])); 
 },   }); 
 } 
 }); 
 } 
 isViewed(materialId: string): boolean { 
 return this.viewedMaterialIds().has(materialId); 
 } 
 openMaterial(materialId: string, url: string): void { 
 const youthId = this.currentYouthId; 
 if (youthId) { 
 this.materials.recordMaterialView(materialId, youthId).subscribe({ 
 next: () => { 
 this.viewedMaterialIds.update((set) => new Set([...set, materialId])); 
 },   }); 
 } 
 window.open(url, '_blank'); 
 } 
 totalPages(total: number, pageSize: number): number { 
 if (!pageSize) return 1; 
 return Math.max(1, Math.ceil(total / pageSize)); 
 } 
 prevSuggested(): void { 
 const current = this.suggestedPage$.value; 
 if (current > 1) this.suggestedPage$.next(current - 1); 
 } 
 nextSuggested(total: number): void { 
 const current = this.suggestedPage$.value; 
 if (current < this.totalPages(total, this.suggestedPageSize)) this.suggestedPage$.next(current + 1); 
 } 
 prevCatalog(): void { 
 const current = this.catalogPage$.value; 
 if (current > 1) this.catalogPage$.next(current - 1); 
 } 
 nextCatalog(total: number): void { 
 const current = this.catalogPage$.value; 
 if (current < this.totalPages(total, this.catalogPageSize)) this.catalogPage$.next(current + 1); 
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
 estimateDuration(type: MaterialType): string { 
 switch (type) { 
 case 'VIDEO':   return '6-12 min'; 
 case 'PDF':   return '8-15 min'; 
 default:   return '3-6 min'; 
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



