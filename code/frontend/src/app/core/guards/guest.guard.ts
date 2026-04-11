import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '@core/services/auth.service';

/** Solo para rutas de invitado (ej. login). Si ya hay sesión, redirige al inicio según rol. */
export const guestGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isLoggedIn()) {
    const role = auth.getRole();
    const redirect =
      role === 'JOVEN' ? '/joven/simulacion/nueva' :
      role === 'ADMIN' ? '/admin/dashboard' : '/profesional/dashboard';
    router.navigate([redirect]);
    return false;
  }

  return true;
};

