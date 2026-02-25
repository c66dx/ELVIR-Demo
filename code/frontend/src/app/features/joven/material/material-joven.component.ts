import { Component, inject, signal } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { Observable, of } from 'rxjs';
import { switchMap, map } from 'rxjs/operators';
import { YouthService } from '../../../core/services/youth.service';
import { ApiService } from '../../../core/services/api.service';
import type { MaterialSuggestion } from '../../../core/models/material-suggestion.model';
import type { SupportMaterial } from '../../../core/models/support-material.model';

interface SuggestionWithMaterial extends MaterialSuggestion {
  material?: SupportMaterial;
}

/**
 * Material de apoyo: sección "Sugerido para ti" (por profesional) y "Catálogo".
 * Registra vistas al abrir material para marcar como visto.
 */
@Component({
  selector: 'app-material-joven',
  standalone: true,
  imports: [AsyncPipe],
  templateUrl: './material-joven.component.html',
  styleUrl: './material-joven.component.scss',
})
export class MaterialJovenComponent {
  private youthService = inject(YouthService);
  private api = inject(ApiService);

  viewedMaterialIds = signal<Set<string>>(new Set());

  suggested$: Observable<SuggestionWithMaterial[]> = this.youthService.getCurrentYouthId().pipe(
    switchMap((youthId) =>
      youthId
        ? this.api.getYouthMaterialSuggestions(youthId).pipe(
            switchMap((suggestions) =>
              this.api.getSupportMaterial().pipe(
                map((materials) => {
                  const matMap = new Map(materials.map((m) => [m.id, m]));
                  return suggestions.map((s) => ({
                    ...s,
                    material: matMap.get(s.material_id),
                  }));
                })
              )
            )
          )
        : of([])
    )
  );

  catalog$: Observable<SupportMaterial[]> = this.api.getSupportMaterial();

  constructor() {
    this.youthService.getCurrentYouthId().subscribe((youthId) => {
      if (youthId) {
        this.api.getYouthMaterialViews(youthId).subscribe({
          next: (views) => {
            this.viewedMaterialIds.update((set) => new Set([...set, ...views.map((v) => v.material_id)]));
          },
        });
      }
    });
  }

  isViewed(materialId: string): boolean {
    return this.viewedMaterialIds().has(materialId);
  }

  openMaterial(materialId: string, url: string): void {
    this.youthService.getCurrentYouthId().subscribe((youthId) => {
      if (youthId) {
        this.api.recordMaterialView(materialId, youthId).subscribe({
          next: () => {
            this.viewedMaterialIds.update((set) => new Set([...set, materialId]));
          },
        });
      }
      window.open(url, '_blank');
    });
  }
}
