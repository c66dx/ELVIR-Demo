import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';
import { switchMap, map, shareReplay } from 'rxjs/operators';
import { AuthApiService } from '@core/services/auth-api.service';
import { YouthApiService } from '@core/services/youth-api.service'; 
/** Obtiene el youthId del usuario JOVEN actual (a partir de getMe + lista de jóvenes). */
@Injectable({ providedIn: 'root' })
export class YouthService { 
 private authApi = inject(AuthApiService);
 private youthsApi = inject(YouthApiService); 
 getCurrentYouthId(): Observable<string | null> { 
 return this.authApi.getMe().pipe(   switchMap((me) => { 
 if (!me || me.role !== 'JOVEN') return of(null); 
 if (me.youth_id) return of(String(me.youth_id)); 
 return this.youthsApi.getYouthsPaged({ page: 1, page_size: 1 }).pipe(   map((paged) => (paged.items.length > 0 ? String(paged.items[0].id) : null))   ); 
 }),   shareReplay(1)   ); 
 }
}

