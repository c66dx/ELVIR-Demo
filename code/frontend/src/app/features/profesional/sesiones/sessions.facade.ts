import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';
import type { SessionMode, SessionStatus } from '@core/models/types.model';
import type { PagedResult, SessionWithTemplateLabel } from '@core/services/api-types';
import { SessionApiService } from '@core/services/session-api.service';
import { YouthApiService } from '@core/services/youth-api.service';

export type SessionRow = SessionWithTemplateLabel & {
  youthName: string;
  youthRut?: string;
  youthPhotoUrl?: string;
};

export interface YouthOption {
  id: string;
  display_name: string;
  rut?: string;
  profile_photo_url?: string;
}

export interface SessionFilters {
  page: number;
  pageSize: number;
  youthId?: string;
  search?: string;
  status?: SessionStatus;
  mode?: SessionMode;
  startDate?: string;
  endDate?: string;
}

interface YouthLookupRow {
  id: string;
  display_name: string;
  rut?: string;
  profile_photo_url?: string;
}

@Injectable({ providedIn: 'root' })
export class SessionsFacade {
  private sessions = inject(SessionApiService);
  private youths = inject(YouthApiService);

  getYouthOptions(): Observable<YouthOption[]> {
    return this.youths.getYouths().pipe(
      map((youths) =>
        youths.map((y) => ({
          id: y.id,
          display_name: y.display_name,
          rut: y.rut,
          profile_photo_url: y.profile_photo_url,
        }))
      )
    );
  }

  getSessionsPage(filters: SessionFilters): Observable<PagedResult<SessionRow>> {
    return this.sessions
      .getSessionsWithTemplateLabelPaged({
        page: filters.page,
        page_size: filters.pageSize,
        youth_id: filters.youthId || undefined,
        search: filters.search || undefined,
        status: filters.status || undefined,
        mode: filters.mode || undefined,
        start_date: filters.startDate || undefined,
        end_date: filters.endDate || undefined,
      })
      .pipe(
        switchMap((paged) => {
          const ids = Array.from(new Set(paged.items.map((s) => s.youth_id)));
          if (ids.length === 0) {
            return of({ paged, lookup: [] as YouthLookupRow[] });
          }
          return this.youths.getYouthLookup(ids).pipe(map((lookup) => ({ paged, lookup })));
        }),
        map(({ paged, lookup }) => {
          const youthMap = new Map(lookup.map((y) => [y.id, y]));
          const items = paged.items.map((s) => ({
            ...s,
            youthName: youthMap.get(s.youth_id)?.display_name ?? 'Desconocido',
            youthRut: youthMap.get(s.youth_id)?.rut,
            youthPhotoUrl: youthMap.get(s.youth_id)?.profile_photo_url,
          }));
          return { ...paged, items };
        })
      );
  }
}
