/**
 * Rutas de la app. Login es público (guestGuard). El resto requiere authGuard.
 * jovenGuard y profesionalGuard restringen por rol. Rutas hijas bajo AppShell.
 * Áreas joven / profesional / admin usan loadChildren para chunks perezosos.
 */
import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { guestGuard } from './core/guards/guest.guard';
import { redirectToDashboardGuard } from './core/guards/redirect-dashboard.guard';
import { jovenGuard, profesionalGuard, adminGuard } from './core/guards/role.guard';
import { AppShellComponent } from './layout/app-shell/app-shell.component';
import { LoginComponent } from './features/auth/login/login.component';
import { SessionEndComponent } from './features/joven/simulacion/session-end/session-end.component';
import { ActivateComponent } from './features/auth/activate/activate.component';
import { ChangePasswordComponent } from './features/auth/change-password/change-password.component';
import { RedirectPlaceholderComponent } from './core/components/redirect-placeholder/redirect-placeholder.component';

export const routes: Routes = [
  {
    path: 'login',
    title: 'Iniciar sesión',
    component: LoginComponent,
    canActivate: [guestGuard],
  },
  {
    path: 'activar',
    title: 'Activar cuenta',
    component: ActivateComponent,
    canActivate: [guestGuard],
  },
  {
    path: '',
    component: AppShellComponent,
    canActivate: [authGuard],
    children: [
      {
        path: '',
        component: RedirectPlaceholderComponent,
        canActivate: [redirectToDashboardGuard],
        pathMatch: 'full',
      },
      {
        path: 'session-end',
        title: 'Fin de sesión',
        canActivate: [authGuard],
        component: SessionEndComponent,
      },
      {
        path: 'cambiar-contrasena',
        title: 'Cambiar contraseña',
        canActivate: [authGuard],
        component: ChangePasswordComponent,
      },
      {
        path: 'joven',
        canActivate: [jovenGuard],
        loadChildren: () =>
          import('./features/joven/joven.routes').then((m) => m.JOVEN_ROUTES),
      },
      {
        path: 'profesional',
        canActivate: [profesionalGuard],
        loadChildren: () =>
          import('./features/profesional/profesional.routes').then((m) => m.PROFESIONAL_ROUTES),
      },
      {
        path: 'admin',
        canActivate: [adminGuard],
        loadChildren: () =>
          import('./features/admin/admin.routes').then((m) => m.ADMIN_ROUTES),
      },
    ],
  },
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: '**', redirectTo: 'login' },
];
