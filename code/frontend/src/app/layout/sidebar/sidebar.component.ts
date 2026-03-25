import { Component, inject, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ApiService } from '../../core/services/api.service';
import { UserRole } from '../../core/models/user.model';
import { JOVEN_NAV, PROFESIONAL_NAV, ADMIN_NAV, type NavItem } from '../navigation'; 
 @Component({ 
 selector: 'app-sidebar',   standalone: true,   imports: [RouterLink, RouterLinkActive],   templateUrl: './sidebar.component.html',   styleUrl: './sidebar.component.scss',
})
export class SidebarComponent implements OnInit { 
 private auth = inject(AuthService); 
 private api = inject(ApiService); 
 role = this.auth.getRole(); 
 roleLabel = ''; 
 displayName = ''; 
 avatarUrl: string | null = null; 
 showProfile = !!this.role; 
 jovenItems: NavItem[] = JOVEN_NAV; 
 profesionalItems: NavItem[] = PROFESIONAL_NAV; 
 adminItems: NavItem[] = ADMIN_NAV; 
 get visibleItems(): NavItem[] { 
 if (this.role === 'JOVEN') return this.jovenItems; 
 if (this.role === 'ADMIN') return this.adminItems; 
 return this.profesionalItems; 
 } 
 ngOnInit(): void { 
 if (!this.showProfile) return; 
 this.roleLabel = this.mapRoleLabel(this.role); 
 this.api.getMe().subscribe({ 
 next: (me) => { 
 if (!me) { 
 this.displayName = this.roleLabel || 'Usuario'; 
 return; 
 } 
 const fallbackName = this.nameFromEmail(me.email) || this.roleLabel || 'Usuario'; 
 this.avatarUrl = me.profile_photo_url  ?? null; 
 if (me.role === 'JOVEN' && me.youth_id) { 
 this.api.getYouth(me.youth_id).subscribe({ 
 next: (youth) => { 
 this.displayName = youth?.display_name || fallbackName; 
 if (youth?.profile_photo_url) { 
 this.avatarUrl = youth.profile_photo_url; 
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
 initials(name?: string | null): string { 
 if (!name) return 'U'; 
 const parts = name.trim().split(/\s+/).filter(Boolean); 
 if (parts.length === 0) return 'U'; 
 if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase(); 
 return (parts[0][0] + parts[1][0]).toUpperCase(); 
 } 
 private mapRoleLabel(role: UserRole | null): string { 
 if (role === 'PROFESIONAL') return 'Tutor'; 
 if (role === 'ADMIN') return 'Administrador'; 
 if (role === 'JOVEN') return 'Joven'; 
 return ''; 
 } 
 private nameFromEmail(email?: string | null): string | null { 
 if (!email) return null; 
 const base = email.split('@')[0]?.replace(/[._-]+/g, ' ').trim(); 
 if (!base) return null; 
 return base   .split(' ')   .filter(Boolean)   .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))   .join(' '); 
 }
}


