import { Routes } from '@angular/router';

/** Rutas bajo `/admin` (lazy loading del área de administración). */
export const ADMIN_ROUTES: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  {
    path: 'dashboard',
    title: 'Administración',
    loadComponent: () =>
      import('./dashboard/dashboard-admin.component').then((m) => m.DashboardAdminComponent),
  },
  {
    path: 'usuarios',
    title: 'Usuarios',
    loadComponent: () =>
      import('./usuarios-logs/usuarios-logs.component').then((m) => m.UsuariosLogsComponent),
  },
  {
    path: 'auditoria',
    title: 'Auditoría',
    loadComponent: () => import('./audit-logs/audit-logs.component').then((m) => m.AuditLogsComponent),
  },
  {
    path: 'profesionales',
    children: [
      {
        path: '',
        title: 'Profesionales',
        loadComponent: () =>
          import('./profesionales-list/profesionales-list.component').then((m) => m.ProfesionalesListComponent),
      },
      {
        path: 'nuevo',
        title: 'Nuevo profesional',
        loadComponent: () =>
          import('./profesional-form/profesional-form.component').then((m) => m.ProfesionalFormComponent),
      },
      {
        path: ':professionalId/editar',
        title: 'Editar profesional',
        loadComponent: () =>
          import('./profesional-form/profesional-form.component').then((m) => m.ProfesionalFormComponent),
      },
    ],
  },
  {
    path: 'material',
    title: 'Material',
    loadComponent: () =>
      import('../material/material-list.component').then((m) => m.MaterialListComponent),
  },
  {
    path: 'material/nuevo',
    title: 'Nuevo material',
    loadComponent: () =>
      import('./material-form/material-form.component').then((m) => m.MaterialFormComponent),
  },
];
