import { Component, ElementRef, EventEmitter, HostListener, inject, Input, OnInit, Output } from '@angular/core';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '@core/services/auth.service';
import { AuthApiService } from '@core/services/auth-api.service';
import { YouthApiService } from '@core/services/youth-api.service';
import { ProfessionalApiService } from '@core/services/professional-api.service';
import { ThemeService } from '@core/services/theme.service';
import { UserRole } from '@core/models/user.model';
import { JOVEN_NAV, PROFESIONAL_NAV, ADMIN_NAV, type NavItem } from '../navigation';
import { UploadUrlPipe } from '@core/pipes/upload-url.pipe';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, UploadUrlPipe],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent implements OnInit {
  private auth = inject(AuthService);
  private authApi = inject(AuthApiService);
  private youthsApi = inject(YouthApiService);
  private professionalsApi = inject(ProfessionalApiService);
  private router = inject(Router);
  private elementRef = inject(ElementRef);
  private themeService = inject(ThemeService);

  role = this.auth.getRole();
  roleLabel = '';
  displayName = '';
  avatarUrl: string | null = null;
  avatarLoadFailed = false;
  showProfile = !!this.role;
  accountRoute = '';
  accountLabel = 'Mi cuenta';
  isMenuOpen = false;
  theme = this.themeService.theme;
  @Input() collapsed = false;
  @Output() toggleCollapsed = new EventEmitter<void>();

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

    if (this.role === 'JOVEN') {
      this.accountRoute = '/joven/cuenta';
      this.accountLabel = 'Mi cuenta';
    } else if (this.role === 'PROFESIONAL') {
      this.accountRoute = '/profesional/cuenta';
      this.accountLabel = 'Mi cuenta';
    } else if (this.role === 'ADMIN') {
      this.accountRoute = '/cambiar-contrasena';
      this.accountLabel = 'Mi perfil';
    }

    this.authApi.getMe().subscribe({
      next: (me) => {
        if (!me) {
          this.displayName = this.roleLabel || 'Usuario';
          return;
        }
        const fallbackName = this.nameFromEmail(me.email) || this.roleLabel || 'Usuario';
        this.avatarUrl = me.profile_photo_url ?? null;
        this.avatarLoadFailed = false;
        if (me.role === 'JOVEN' && me.youth_id) {
          this.youthsApi.getYouth(me.youth_id).subscribe({
            next: (youth) => {
              this.displayName = youth?.display_name || fallbackName;
              if (youth?.profile_photo_url) {
                this.avatarUrl = youth.profile_photo_url;
                this.avatarLoadFailed = false;
              }
            },
            error: () => (this.displayName = fallbackName),
          });
          return;
        }
        if (me.role === 'PROFESIONAL' && me.professional_id) {
          this.professionalsApi.getProfessional(me.professional_id).subscribe({
            next: (prof) => {
              this.displayName = prof?.display_name || fallbackName;
            },
            error: () => (this.displayName = fallbackName),
          });
          return;
        }
        this.displayName = fallbackName;
      },
      error: () => {
        this.displayName = this.roleLabel || 'Usuario';
      },
    });
  }

  initials(name?: string | null): string {
    if (!name) return 'U';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return 'U';
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

  toggleTheme(): void {
    this.themeService.toggle();
  }

  onToggleCollapsed(): void {
    this.toggleCollapsed.emit();
  }


  toggleMenu(): void {
    this.isMenuOpen = !this.isMenuOpen;
  }

  closeMenu(): void {
    this.isMenuOpen = false;
  }

  onLogout(): void {
    const confirmed = window.confirm('¿Seguro que quieres cerrar sesión?');
    if (!confirmed) return;
    this.authApi.logout().subscribe({
      complete: () => {
        this.auth.logout();
        this.router.navigate(['/login']);
      },
    });
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event): void {
    if (!this.isMenuOpen) return;
    if (!this.elementRef.nativeElement.contains(event.target as Node)) {
      this.closeMenu();
    }
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
    return base
      .split(' ')
      .filter(Boolean)
      .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
      .join(' ');
  }
}
