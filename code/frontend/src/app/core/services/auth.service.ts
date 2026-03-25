import { Injectable } from '@angular/core';
import { UserRole } from '../models/user.model'; 
 const ROLE_KEY = 'elvir_role';
const TOKEN_KEY = 'elvir_token'; 
 /**   * Servicio de autenticacin.   *   * La autenticacin principal usa cookie HttpOnly emitida por backend.   * En frontend solo persistimos el rol para routing/UI.   */
@Injectable({ providedIn: 'root' })
export class AuthService { 
 private storage = window.sessionStorage; 
 getToken(): string | null { 
 return this.storage.getItem(TOKEN_KEY); 
 } 
 getRole(): UserRole | null { 
 const role = this.storage.getItem(ROLE_KEY); 
 return role === 'JOVEN' || role === 'PROFESIONAL' || role === 'ADMIN' ? role : null; 
 } 
 isLoggedIn(): boolean { 
 return !!this.getRole(); 
 } 
 setSession(_token: string, role: UserRole): void { 
 if (_token) { 
 this.storage.setItem(TOKEN_KEY, _token); 
 } 
 this.storage.setItem(ROLE_KEY, role); 
 } 
 logout(): void { 
 this.storage.removeItem(ROLE_KEY); 
 this.storage.removeItem(TOKEN_KEY); 
 }
}

