import { Injectable } from '@angular/core';
import { UserRole } from '../models/user.model';

const TOKEN_KEY = 'elvir_token';
const ROLE_KEY = 'elvir_role';

/**
 * Servicio de autenticación. Gestiona token y rol en localStorage.
 * El login se hace vía ApiService contra el backend; setSession guarda el resultado.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  getRole(): UserRole | null {
    const role = localStorage.getItem(ROLE_KEY);
    return role === 'JOVEN' || role === 'PROFESIONAL' || role === 'ADMIN' ? role : null;
  }

  isLoggedIn(): boolean {
    return !!this.getToken() && !!this.getRole();
  }

  setSession(token: string, role: UserRole): void {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(ROLE_KEY, role);
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
  }
}
