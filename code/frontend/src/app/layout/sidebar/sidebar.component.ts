import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { UserRole } from '../../core/models/user.model';

interface NavItem {
  label: string;
  route: string;
  roles: UserRole[];
  exact?: boolean;
  icon: string;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent {
  private auth = inject(AuthService);
  role = this.auth.getRole();

  jovenItems: NavItem[] = [
    { label: 'Dashboard', route: '/joven/dashboard', roles: ['JOVEN'], exact: true, icon: 'dashboard' },
    { label: 'Nueva Simulación', route: '/joven/simulacion/nueva', roles: ['JOVEN'], exact: true, icon: 'play' },
    { label: 'Historial', route: '/joven/historial', roles: ['JOVEN'], exact: true, icon: 'history' },
    { label: 'Material', route: '/joven/material', roles: ['JOVEN'], exact: true, icon: 'material' },
  ];

  profesionalItems: NavItem[] = [
    { label: 'Dashboard', route: '/profesional/dashboard', roles: ['PROFESIONAL'], exact: true, icon: 'dashboard' },
    { label: 'Jóvenes', route: '/profesional/jovenes', roles: ['PROFESIONAL'], exact: true, icon: 'users' },
    { label: 'Crear Joven', route: '/profesional/jovenes/nuevo', roles: ['PROFESIONAL'], exact: true, icon: 'user-plus' },
    { label: 'Crear Material', route: '/profesional/material/nuevo', roles: ['PROFESIONAL'], exact: true, icon: 'material' },
  ];

  adminItems: NavItem[] = [
    { label: 'Dashboard', route: '/admin/dashboard', roles: ['ADMIN'], exact: true, icon: 'dashboard' },
    { label: 'Crear Profesional', route: '/admin/profesionales/nuevo', roles: ['ADMIN'], exact: true, icon: 'user-plus' },
    { label: 'Crear Material', route: '/admin/material/nuevo', roles: ['ADMIN'], exact: true, icon: 'material' },
  ];

  get visibleItems(): NavItem[] {
    if (this.role === 'JOVEN') return this.jovenItems;
    if (this.role === 'ADMIN') return this.adminItems;
    return this.profesionalItems;
  }
}
