import { Injectable } from '@angular/core';
import { UserRole } from '../models/user.model';

const ROLE_KEY = 'elvir_role';

/**
 * Servicio de autenticación.
 *
 * La autenticación principal usa cookie HttpOnly emitida por backend.
 * En frontend solo persistimos el rol para routing/UI.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private storage = window.sessionStorage;

  getToken(): string | null {
    return null;
  }

  getRole(): UserRole | null {
    const role = this.storage.getItem(ROLE_KEY);
    return role === 'JOVEN' || role === 'PROFESIONAL' || role === 'ADMIN' ? role : null;
  }

  isLoggedIn(): boolean {
    return !!this.getRole();
  }

  setSession(_token: string, role: UserRole): void {
    this.storage.setItem(ROLE_KEY, role);
  }

  logout(): void {
    this.storage.removeItem(ROLE_KEY);
  }
}

