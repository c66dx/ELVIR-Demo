import { Component, ElementRef, HostListener, inject, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ApiService } from '../../core/services/api.service';
import { ThemeService } from '../../core/services/theme.service';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './topbar.component.html',
  styleUrl: './topbar.component.scss',
})
export class TopbarComponent implements OnInit {
  private auth = inject(AuthService);
  private api = inject(ApiService);
  private router = inject(Router);
  private elementRef = inject(ElementRef);
  private themeService = inject(ThemeService);
  role = this.auth.getRole();
  roleLabel = '';
  displayName = '';
  avatarUrl: string | null = null;
  isMenuOpen = false;
  accountRoute = '';
  accountLabel = 'Mi Cuenta';
  theme = this.themeService.theme;

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
      this.accountLabel = 'Cambiar contraseña';
    }
    this.api.getMe().subscribe({
      next: (me) => {
        if (!me) {
          this.displayName = this.roleLabel || 'Usuario';
          return;
        }
        const fallbackName = this.nameFromEmail(me.email) || this.roleLabel || 'Usuario';
        this.avatarUrl = me.profile_photo_url ?? null;

        if (me.role === 'JOVEN' && me.youth_id) {
          this.api.getYouth(me.youth_id).subscribe({
            next: (youth) => {
              this.displayName = youth?.display_name || fallbackName;
              if (youth?.profile_photo_url) {
                this.avatarUrl = youth.profile_photo_url;
              }
            },
            error: () => (this.displayName = fallbackName),
          });
          return;
        }

        if (me.role === 'PROFESIONAL' && me.professional_id) {
          this.api.getProfessional(me.professional_id).subscribe({
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

  onLogout(): void {
    const confirmed = window.confirm('¿Seguro que quieres cerrar sesión?');
    if (!confirmed) return;
    this.api.logout().subscribe({
      complete: () => {
        this.auth.logout();
        this.router.navigate(['/login']);
      },
    });
  }

  toggleMenu(): void {
    this.isMenuOpen = !this.isMenuOpen;
  }

  toggleTheme(): void {
    this.themeService.toggle();
  }

  closeMenu(): void {
    this.isMenuOpen = false;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event): void {
    if (!this.isMenuOpen) return;
    if (!this.elementRef.nativeElement.contains(event.target as Node)) {
      this.closeMenu();
    }
  }

  initials(name?: string | null): string {
    if (!name) return 'U';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return 'U';
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
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
    return base
      .split(' ')
      .filter(Boolean)
      .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
      .join(' ');
  }
}
