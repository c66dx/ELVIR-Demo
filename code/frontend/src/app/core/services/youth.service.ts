import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';
import { switchMap, map, shareReplay } from 'rxjs/operators';
import { ApiService } from './api.service';

/** Obtiene el youthId del usuario JOVEN actual (a partir de getMe + lista de jóvenes). */
@Injectable({ providedIn: 'root' })
export class YouthService {
  private api = inject(ApiService);

  getCurrentYouthId(): Observable<string | null> {
    return this.api.getMe().pipe(
      switchMap((me) => {
        if (!me || me.role !== 'JOVEN') return of(null);
        if (me.youth_id) return of(String(me.youth_id));
        return this.api.getYouths().pipe(
          map((youths) => (youths.length > 0 ? String(youths[0].id) : null))
        );
      }),
      shareReplay(1)
    );
  }
}
