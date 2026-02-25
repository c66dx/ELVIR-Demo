import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { UserRole } from '../models/user.model';

/** Crea un guard que restringe la ruta a un rol concreto (JOVEN o PROFESIONAL). */
export function createRoleGuard(allowedRole: UserRole): CanActivateFn {
  return () => {
    const auth = inject(AuthService);
    const router = inject(Router);

    if (!auth.isLoggedIn()) {
      router.navigate(['/login']);
      return false;
    }

    const role = auth.getRole();
    if (role !== allowedRole) {
      const redirect =
        role === 'JOVEN' ? '/joven/dashboard' :
        role === 'ADMIN' ? '/admin/dashboard' : '/profesional/dashboard';
      router.navigate([redirect]);
      return false;
    }

    return true;
  };
}

export const jovenGuard = createRoleGuard('JOVEN');
export const profesionalGuard = createRoleGuard('PROFESIONAL');
export const adminGuard = createRoleGuard('ADMIN');
