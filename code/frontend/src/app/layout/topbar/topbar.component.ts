import { Component, ElementRef, HostListener, inject, OnDestroy, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Subscription, timer } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';
import { ApiService } from '../../core/services/api.service';
import { ThemeService } from '../../core/services/theme.service';
import { YouthNotificationsService, YouthNotification } from '../../core/services/youth-notifications.service';
import { UploadUrlPipe } from '../../core/pipes/upload-url.pipe';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [RouterLink, UploadUrlPipe],
  templateUrl: './topbar.component.html',
  styleUrl: './topbar.component.scss',
})
export class TopbarComponent implements OnInit, OnDestroy { 
 private auth = inject(AuthService); 
 private api = inject(ApiService); 
 private router = inject(Router); 
 private elementRef = inject(ElementRef); 
 private themeService = inject(ThemeService); 
 private youthNotifications = inject(YouthNotificationsService); 
 role = this.auth.getRole(); 
 roleLabel = ''; 
 displayName = ''; 
 avatarUrl: string | null = null;
 /** Evita mostrar texto alt cuando la imagen falla (404, host distinto, etc.). */
 avatarLoadFailed = false;
 isMenuOpen = false; 
 isNotifOpen = false; 
 notifications: YouthNotification[] = []; 
 private youthId: string | null = null; 
 notificationsTotal = 0; 
 notificationsUnread = 0; 
 accountRoute = ''; 
 accountLabel = 'Mi Cuenta'; 
 theme = this.themeService.theme; 
 private notifPollSub?: Subscription; 
 private readonly notifPollIntervalMs = 30000; 
 ngOnInit(): void { 
 this.roleLabel = this.mapRoleLabel(this.role); 
 if (this.role === 'JOVEN') { 
 this.accountRoute = '/joven/cuenta'; 
 this.accountLabel = 'Mi Cuenta'; 
 } else if (this.role === 'PROFESIONAL') { 
 this.accountRoute = '/profesional/cuenta'; 
 this.accountLabel = 'Mi Cuenta'; 
 } else if (this.role === 'ADMIN') { 
 this.accountRoute = '/cambiar-contrasena'; 
 this.accountLabel = 'Mi perfil'; 
 } 
 this.api.getMe().subscribe({ 
 next: (me) => { 
 if (!me) { 
 this.displayName = this.roleLabel || 'Usuario'; 
 return; 
 } 
 const fallbackName = this.nameFromEmail(me.email) || this.roleLabel || 'Usuario'; 
 this.avatarUrl = me.profile_photo_url ?? null;
 this.avatarLoadFailed = false;
 if (me.role === 'JOVEN' && me.youth_id) { 
 this.youthId = me.youth_id; 
 this.startNotificationsPolling(); 
 this.api.getYouth(me.youth_id).subscribe({ 
 next: (youth) => { 
 this.displayName = youth?.display_name || fallbackName; 
 if (youth?.profile_photo_url) {
 this.avatarUrl = youth.profile_photo_url;
 this.avatarLoadFailed = false;
 }
 },   error: () => (this.displayName = fallbackName),   }); 
 return; 
 } 
 if (me.role === 'PROFESIONAL' && me.professional_id) { 
 this.api.getProfessional(me.professional_id).subscribe({ 
 next: (prof) => { 
 this.displayName = prof?.display_name || fallbackName; 
 },   error: () => (this.displayName = fallbackName),   }); 
 return; 
 } 
 this.displayName = fallbackName; 
 },   error: () => { 
 this.displayName = this.roleLabel || 'Usuario'; 
 },   }); 
 } 
 ngOnDestroy(): void { 
 this.stopNotificationsPolling(); 
 } 
 get unreadBadge(): string { 
 return this.notificationsUnread > 9 ? '9+' : String(this.notificationsUnread); 
 } 
 notifAriaLabel(): string { 
 if (this.notificationsUnread === 0) return 'Notificaciones'; 
 return `Notificaciones, ${this.notificationsUnread} sin leer`; 
 } 
 onLogout(): void { 
    const confirmed = window.confirm('¿Seguro que quieres cerrar sesión?');
 if (!confirmed) return; 
 this.api.logout().subscribe({ 
 complete: () => { 
 this.auth.logout(); 
 this.router.navigate(['/login']); 
 },   }); 
 } 
 toggleMenu(): void { 
 this.isMenuOpen = !this.isMenuOpen; 
 if (this.isMenuOpen) { 
 this.closeNotifications(); 
 } 
 } 
 toggleNotifications(): void { 
 this.isNotifOpen = !this.isNotifOpen; 
 if (this.isNotifOpen) { 
 this.closeMenu(); 
 this.refreshNotifications(); 
 } 
 } 
 toggleTheme(): void { 
 this.themeService.toggle(); 
 } 
 closeMenu(): void { 
 this.isMenuOpen = false; 
 } 
 closeNotifications(): void { 
 this.isNotifOpen = false; 
 } 
 markAsRead(item: YouthNotification): void { 
 if (!this.youthId || item.read) return; 
 this.notifications = this.notifications.map((entry) =>   entry.id === item.id ? { ...entry, read: true } : entry   ); 
 this.notificationsUnread = Math.max(0, this.notificationsUnread - 1); 
 this.youthNotifications.markAsRead(this.youthId, item.id).subscribe(); 
 } 
 markAllRead(): void { 
 if (!this.youthId) return; 
 this.notifications = this.notifications.map((entry) => ({ ...entry, read: true })); 
 this.notificationsUnread = 0; 
 this.youthNotifications.markAllRead(this.youthId).subscribe(); 
 } 
@HostListener('document:click', ['$event'])
onDocumentClick(event: Event): void { 
 if (!this.isMenuOpen && !this.isNotifOpen) return; 
 if (!this.elementRef.nativeElement.contains(event.target as Node)) { 
 this.closeMenu(); 
 this.closeNotifications(); 
 } 
 } 
 initials(name?: string | null): string { 
 if (!name) return 'U'; 
 const parts = name.trim().split(/\s+/).filter(Boolean); 
 if (parts.length === 0) return 'U'; 
 if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase(); 
 return (parts[0][0] + parts[1][0]).toUpperCase(); 
 } 
 private refreshNotifications(): void { 
 if (!this.youthId) return; 
 this.youthNotifications.getYouthNotifications(this.youthId, { page: 1, page_size: 4 }).subscribe({ 
 next: (paged) => { 
 this.notifications = paged.items; 
 this.notificationsTotal = paged.total; 
 this.notificationsUnread = paged.unread; 
 },   }); 
 } 
 private startNotificationsPolling(): void { 
 if (!this.youthId || this.notifPollSub) return; 
 this.refreshNotifications(); 
 this.notifPollSub = timer(this.notifPollIntervalMs, this.notifPollIntervalMs).subscribe(() => this.refreshNotifications()); 
 } 
 private stopNotificationsPolling(): void { 
 if (!this.notifPollSub) return; 
 this.notifPollSub.unsubscribe(); 
 this.notifPollSub = undefined; 
 } 
 private mapRoleLabel(role: string | null): string { 
 if (role === 'JOVEN') return 'Joven'; 
 if (role === 'PROFESIONAL') return 'Tutor'; 
 if (role === 'ADMIN') return 'Administrador'; 
 return ''; 
 } 
 private nameFromEmail(email?: string | null): string | null { 
 if (!email) return null; 
 const base = email.split('@')[0]?.replace(/[._-]+/g, ' ').trim(); 
 if (!base) return null; 
 return base   .split(' ')   .filter(Boolean)   .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))   .join(' '); 
 }
}
