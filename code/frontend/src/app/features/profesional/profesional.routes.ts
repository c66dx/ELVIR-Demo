import { Routes } from '@angular/router';
import { profesionalGuard } from '@core/guards/role.guard';
import { interviewLeaveGuard } from '@core/guards/interview-leave.guard';

/** Rutas bajo `/profesional` (carga perezosa). */
export const PROFESIONAL_ROUTES: Routes = [
  {
    path: 'dashboard',
    title: 'Panel tutor',
    canActivate: [profesionalGuard],
    loadComponent: () =>
      import('./dashboard/dashboard-profesional.component').then((m) => m.DashboardProfesionalComponent),
  },
  {
    path: 'material',
    canActivate: [profesionalGuard],
    children: [
      {
        path: '',
        title: 'Material',
        loadComponent: () =>
          import('../material/material-list.component').then((m) => m.MaterialListComponent),
      },
      {
        path: 'nuevo',
        title: 'Nuevo material',
        loadComponent: () =>
          import('../admin/material-form/material-form.component').then((m) => m.MaterialFormComponent),
      },
    ],
  },
  {
    path: 'sesiones',
    title: 'Sesiones',
    canActivate: [profesionalGuard],
    loadComponent: () =>
      import('./sesiones/sessions-list.component').then((m) => m.SessionsListComponent),
  },
  {
    path: 'sesiones/:sessionId',
    title: 'Detalle de sesión',
    canActivate: [profesionalGuard],
    loadComponent: () =>
      import('./sesiones/session-view.component').then((m) => m.SessionViewComponent),
  },
  {
    path: 'simulacion',
    children: [
      {
        path: ':sessionId',
        children: [
          {
            path: 'preparacion',
            title: 'Preparación',
            canActivate: [profesionalGuard],
            loadComponent: () =>
              import('@core/components/interview-preparation/interview-preparation.component').then(
                (m) => m.InterviewPreparationComponent,
              ),
            data: { target: 'profesional' },
          },
          {
            path: 'espera',
            title: 'Sala de espera',
            canActivate: [profesionalGuard],
            loadComponent: () =>
              import('@core/components/interview-waiting-room/interview-waiting-room.component').then(
                (m) => m.InterviewWaitingRoomComponent,
              ),
            data: { target: 'profesional' },
          },
          {
            path: '',
            title: 'Simulación',
            canActivate: [profesionalGuard],
            canDeactivate: [interviewLeaveGuard],
            loadComponent: () =>
              import('../joven/simulacion/simulacion-detail.component').then((m) => m.SimulacionDetailComponent),
          },
        ],
      },
    ],
  },
  {
    path: 'cuenta',
    title: 'Mi cuenta',
    canActivate: [profesionalGuard],
    loadComponent: () =>
      import('./account/professional-account.component').then((m) => m.ProfessionalAccountComponent),
  },
  {
    path: 'jovenes',
    canActivate: [profesionalGuard],
    children: [
      {
        path: '',
        title: 'Jóvenes',
        loadComponent: () =>
          import('./jovenes/jovenes-list.component').then((m) => m.JovenesListComponent),
      },
      {
        path: 'nuevo',
        title: 'Nuevo joven',
        loadComponent: () =>
          import('./jovenes/joven-form.component').then((m) => m.JovenFormComponent),
      },
      {
        path: ':youthId',
        loadComponent: () =>
          import('./jovenes/joven-detail-wrapper.component').then((m) => m.JovenDetailWrapperComponent),
        children: [
          {
            path: '',
            title: 'Perfil joven',
            loadComponent: () =>
              import('./jovenes/perfil-joven.component').then((m) => m.PerfilJovenComponent),
          },
          {
            path: 'editar',
            title: 'Editar joven',
            loadComponent: () =>
              import('./jovenes/joven-form.component').then((m) => m.JovenFormComponent),
          },
          {
            path: 'supervisada',
            children: [
              {
                path: 'nueva',
                title: 'Simulación supervisada',
                loadComponent: () =>
                  import('./jovenes/supervisada/supervised-start.component').then(
                    (m) => m.SupervisedStartComponent,
                  ),
              },
            ],
          },
        ],
      },
    ],
  },
];

