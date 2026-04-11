import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { BehaviorSubject, combineLatest, of } from 'rxjs';
import { switchMap, take } from 'rxjs/operators';
import { YouthService } from '@core/services/youth.service';
import { 
 YouthNotificationsService,   type YouthNotification,
} from '@core/services/youth-notifications.service'; 
 @Component({ 
 selector: 'app-notifications-joven',   standalone: true,   imports: [AsyncPipe, RouterLink],   templateUrl: './notifications-joven.component.html',   styleUrl: './notifications-joven.component.scss',
 changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotificationsJovenComponent { 
 private youthService = inject(YouthService); 
 private notifications = inject(YouthNotificationsService); 
 private page$ = new BehaviorSubject(1); 
 private refresh$ = new BehaviorSubject(0); 
 readonly pageSize = 12; 
 data$ = combineLatest([this.youthService.getCurrentYouthId(), this.page$, this.refresh$]).pipe(   switchMap(([youthId, page]) =>   youthId   ?  this.notifications.getYouthNotifications(youthId, { page, page_size: this.pageSize })   : of({ items: [], total: 0, unread: 0, page: 1, page_size: this.pageSize })   )   ); 
 totalPages(total: number): number { 
 return Math.max(1, Math.ceil(total / this.pageSize)); 
 } 
 prevPage(): void { 
 const current = this.page$.value; 
 if (current > 1) this.page$.next(current - 1); 
 } 
 nextPage(total: number): void { 
 const current = this.page$.value; 
 if (current < this.totalPages(total)) this.page$.next(current + 1); 
 } 
 markAsRead(item: YouthNotification): void { 
 if (item.read) return; 
 this.youthService.getCurrentYouthId().pipe(take(1)).subscribe((youthId) => { 
 if (!youthId) return; 
 this.notifications.markAsRead(youthId, item.id).subscribe(() => this.refresh()); 
 }); 
 } 
 markAllRead(): void { 
 this.youthService.getCurrentYouthId().pipe(take(1)).subscribe((youthId) => { 
 if (!youthId) return; 
 this.notifications.markAllRead(youthId).subscribe(() => this.refresh()); 
 }); 
 } 
 refresh(): void { 
 this.refresh$.next(this.refresh$.value + 1); 
 }
}

