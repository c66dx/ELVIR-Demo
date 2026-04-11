import { Injectable, inject } from '@angular/core';
import { forkJoin } from 'rxjs';
import { CatalogApiService } from '@core/services/catalog-api.service';
import { SessionApiService } from '@core/services/session-api.service';

@Injectable({ providedIn: 'root' })
export class NuevaSimulacionFacade {
  private catalog = inject(CatalogApiService);
  private sessions = inject(SessionApiService);

  loadCatalogs() {
    return forkJoin({
      jobRoles: this.catalog.getJobRoles(),
      cases: this.catalog.getCases(),
    });
  }

  getSimulationTemplates(params: { job_role_id?: string; case_id?: string }) {
    return this.catalog.getSimulationTemplates(params);
  }

  createSession(data: {
    youth_id: string;
    simulation_template_id: string;
    mode: 'AUTOGESTIONADA' | 'SUPERVISADA';
    professional_id?: string;
  }) {
    return this.sessions.createSession(data);
  }
}
