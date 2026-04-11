import { Routes } from '@angular/router';
import { jovenGuard } from '@core/guards/role.guard';
import { interviewLeaveGuard } from '@core/guards/interview-leave.guard';

/** Rutas bajo `/joven` (carga perezosa). */
export const JOVEN_ROUTES: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'simulacion/nueva' },
  {
    path: 'simulacion',
    children: [
      {
        path: 'nueva',
        title: 'Nueva simulación',
        canActivate: [jovenGuard],
        loadComponent: () =>
          import('./simulacion/nueva-simulacion.component').then((m) => m.NuevaSimulacionComponent),
      },
      {
        path: ':sessionId',
        children: [
          {
            path: 'preparacion',
            title: 'Preparación',
            canActivate: [jovenGuard],
            loadComponent: () =>
              import('@core/components/interview-preparation/interview-preparation.component').then(
                (m) => m.InterviewPreparationComponent,
              ),
            data: { target: 'joven' },
          },
          {
            path: 'espera',
            title: 'Sala de espera',
            canActivate: [jovenGuard],
            loadComponent: () =>
              import('@core/components/interview-waiting-room/interview-waiting-room.component').then(
                (m) => m.InterviewWaitingRoomComponent,
              ),
            data: { target: 'joven' },
          },
          {
            path: '',
            title: 'Simulación',
            canActivate: [jovenGuard],
            canDeactivate: [interviewLeaveGuard],
            loadComponent: () =>
              import('./simulacion/simulacion-detail.component').then((m) => m.SimulacionDetailComponent),
          },
        ],
      },
    ],
  },
  {
    path: 'historial',
    title: 'Historial',
    canActivate: [jovenGuard],
    loadComponent: () =>
      import('./historial/historial-joven.component').then((m) => m.HistorialJovenComponent),
  },
  {
    path: 'retroalimentacion',
    children: [
      {
        path: ':sessionId',
        title: 'Retroalimentación',
        canActivate: [jovenGuard],
        loadComponent: () =>
          import('./retroalimentacion/retroalimentacion-detail.component').then(
            (m) => m.RetroalimentacionDetailJovenComponent,
          ),
      },
      {
        path: '',
        title: 'Retroalimentación',
        canActivate: [jovenGuard],
        loadComponent: () =>
          import('./retroalimentacion/retroalimentacion.component').then((m) => m.RetroalimentacionJovenComponent),
      },
    ],
  },
  {
    path: 'material',
    title: 'Material de apoyo',
    canActivate: [jovenGuard],
    loadComponent: () =>
      import('./material/material-joven.component').then((m) => m.MaterialJovenComponent),
  },
  {
    path: 'notificaciones',
    title: 'Notificaciones',
    canActivate: [jovenGuard],
    loadComponent: () =>
      import('./notificaciones/notifications-joven.component').then((m) => m.NotificationsJovenComponent),
  },
  {
    path: 'cuenta',
    title: 'Mi cuenta',
    canActivate: [jovenGuard],
    loadComponent: () => import('./account/account.component').then((m) => m.MyAccountComponent),
  },
];

