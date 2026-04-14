import { UserRole } from '@core/models/user.model';

export interface NavItem {
  label: string;
  route: string;
  roles: UserRole[];
  exact?: boolean;
  icon: string;
}

export const JOVEN_NAV: NavItem[] = [
  { label: 'Entrevista', route: '/joven/simulacion/nueva', roles: ['JOVEN'], exact: true, icon: 'play' },
  { label: 'Mis prácticas', route: '/joven/historial', roles: ['JOVEN'], exact: true, icon: 'history' },
  { label: 'Retroalimentación', route: '/joven/retroalimentacion', roles: ['JOVEN'], exact: false, icon: 'message' },
  { label: 'Material', route: '/joven/material', roles: ['JOVEN'], exact: true, icon: 'material' },
  { label: 'Notificaciones', route: '/joven/notificaciones', roles: ['JOVEN'], exact: true, icon: 'bell' },
];

export const PROFESIONAL_NAV: NavItem[] = [
  { label: 'Dashboard', route: '/profesional/dashboard', roles: ['PROFESIONAL'], exact: true, icon: 'dashboard' },
  { label: 'Jóvenes', route: '/profesional/jovenes', roles: ['PROFESIONAL'], exact: false, icon: 'users' },
  { label: 'Entrevistas', route: '/profesional/sesiones', roles: ['PROFESIONAL'], exact: true, icon: 'history' },
  { label: 'Material', route: '/profesional/material', roles: ['PROFESIONAL'], exact: false, icon: 'material' },
];

export const ADMIN_NAV: NavItem[] = [
  { label: 'Dashboard', route: '/admin/dashboard', roles: ['ADMIN'], exact: true, icon: 'dashboard' },
  { label: 'Usuarios y logs', route: '/admin/usuarios', roles: ['ADMIN'], exact: true, icon: 'users' },
  { label: 'Auditoría', route: '/admin/auditoria', roles: ['ADMIN'], exact: true, icon: 'history' },
  { label: 'Tutores', route: '/admin/profesionales', roles: ['ADMIN'], exact: false, icon: 'users' },
  { label: 'Material', route: '/admin/material', roles: ['ADMIN'], exact: false, icon: 'material' },
  { label: 'Mi perfil', route: '/cambiar-contrasena', roles: ['ADMIN'], exact: true, icon: 'lock' },
];

export function getNavItemsForRole(role: UserRole | null): NavItem[] {
  if (role === 'JOVEN') return JOVEN_NAV;
  if (role === 'PROFESIONAL') return PROFESIONAL_NAV;
  if (role === 'ADMIN') return ADMIN_NAV;
  return [];
}
