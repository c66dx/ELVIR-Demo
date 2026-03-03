/**
 * Rutas de la app. Login es público (guestGuard). El resto requiere authGuard.
 * jovenGuard y profesionalGuard restringen por rol. Rutas hijas bajo AppShell.
 */
import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { guestGuard } from './core/guards/guest.guard';
import { redirectToDashboardGuard } from './core/guards/redirect-dashboard.guard';
import { jovenGuard, profesionalGuard, adminGuard } from './core/guards/role.guard';
import { AppShellComponent } from './layout/app-shell/app-shell.component';
import { LoginComponent } from './features/auth/login/login.component';
import { DashboardJovenComponent } from './features/joven/dashboard/dashboard-joven.component';
import { NuevaSimulacionComponent } from './features/joven/simulacion/nueva-simulacion.component';
import { SimulacionDetailComponent } from './features/joven/simulacion/simulacion-detail.component';
import { SessionEndComponent } from './features/joven/simulacion/session-end/session-end.component';
import { HistorialJovenComponent } from './features/joven/historial/historial-joven.component';
import { MaterialJovenComponent } from './features/joven/material/material-joven.component';
import { DashboardProfesionalComponent } from './features/profesional/dashboard/dashboard-profesional.component';
import { JovenesListComponent } from './features/profesional/jovenes/jovenes-list.component';
import { JovenFormComponent } from './features/profesional/jovenes/joven-form.component';
import { PerfilJovenComponent } from './features/profesional/jovenes/perfil-joven.component';
import { JovenDetailWrapperComponent } from './features/profesional/jovenes/joven-detail-wrapper.component';
import { SupervisedStartComponent } from './features/profesional/jovenes/supervisada/supervised-start.component';
import { ActivateComponent } from './features/auth/activate/activate.component';
import { ChangePasswordComponent } from './features/auth/change-password/change-password.component';
import { DashboardAdminComponent } from './features/admin/dashboard/dashboard-admin.component';
import { ProfesionalFormComponent } from './features/admin/profesional-form/profesional-form.component';
import { ProfesionalesListComponent } from './features/admin/profesionales-list/profesionales-list.component';
import { MaterialFormComponent } from './features/admin/material-form/material-form.component';
import { RedirectPlaceholderComponent } from './core/components/redirect-placeholder/redirect-placeholder.component';

export const routes: Routes = [
  {
    path: 'login',
    component: LoginComponent,
    canActivate: [guestGuard],
  },
  {
    path: 'activar',
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
        canActivate: [authGuard],
        component: SessionEndComponent,
      },
      {
        path: 'cambiar-contrasena',
        canActivate: [authGuard],
        component: ChangePasswordComponent,
      },
      {
        path: 'joven/simulacion/nueva',
        canActivate: [jovenGuard],
        component: NuevaSimulacionComponent,
      },
      {
        path: 'joven/simulacion/:sessionId',
        canActivate: [authGuard],
        component: SimulacionDetailComponent,
      },
      {
        path: 'joven',
        canActivate: [jovenGuard],
        children: [
          { path: 'dashboard', component: DashboardJovenComponent },
          { path: 'historial', component: HistorialJovenComponent },
          { path: 'material', component: MaterialJovenComponent },
        ],
      },
      {
        path: 'profesional',
        canActivate: [profesionalGuard],
        children: [
          { path: 'dashboard', component: DashboardProfesionalComponent },
          { path: 'material/nuevo', component: MaterialFormComponent },
          {
            path: 'jovenes',
            children: [
              { path: '', component: JovenesListComponent },
              { path: 'nuevo', component: JovenFormComponent },
              {
                path: ':youthId',
                component: JovenDetailWrapperComponent,
                children: [
                  { path: '', component: PerfilJovenComponent },
                  { path: 'editar', component: JovenFormComponent },
                  { path: 'supervisada/nueva', component: SupervisedStartComponent },
                ],
              },
            ],
          },
        ],
      },
      {
        path: 'admin',
        canActivate: [adminGuard],
        children: [
          { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
          { path: 'dashboard', component: DashboardAdminComponent },
          {
            path: 'profesionales',
            children: [
              { path: '', component: ProfesionalesListComponent },
              { path: 'nuevo', component: ProfesionalFormComponent },
              { path: ':professionalId/editar', component: ProfesionalFormComponent },
            ],
          },
          { path: 'material/nuevo', component: MaterialFormComponent },
        ],
      },
    ],
  },
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: '**', redirectTo: 'login' },
];
