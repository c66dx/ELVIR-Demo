import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/**
 * Redirige la ruta raíz al inicio según el rol del usuario.
 * Solo se usa en rutas protegidas por authGuard (usuario ya autenticado).
 */
export const redirectToDashboardGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const role = auth.getRole();
  const path =
    role === 'JOVEN' ? '/joven/simulacion/nueva' :
    role === 'ADMIN' ? '/admin/dashboard' : '/profesional/dashboard';

  return router.createUrlTree([path]);
};

