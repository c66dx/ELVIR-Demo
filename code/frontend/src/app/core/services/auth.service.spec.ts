import { AuthService } from '@core/services/auth.service'; 
 describe('AuthService', () => { 
 let service: AuthService; 
 beforeEach(() => { 
 window.sessionStorage.clear(); 
 service = new AuthService(); 
 }); 
 afterEach(() => { 
 window.sessionStorage.clear(); 
 }); 
 it('stores and returns valid role and token', () => { 
 service.setSession('ignored-token', 'JOVEN'); 
 expect(service.getToken()).toBe('ignored-token'); 
 expect(service.getRole()).toBe('JOVEN'); 
 expect(service.isLoggedIn()).toBeTrue(); 
 }); 
 it('returns null for invalid role persisted in storage', () => { 
 window.sessionStorage.setItem('elvir_role', 'INVALID'); 
 expect(service.getRole()).toBeNull(); 
 expect(service.isLoggedIn()).toBeFalse(); 
 }); 
 it('logout clears stored role', () => { 
 service.setSession('ignored-token', 'ADMIN'); 
 service.logout(); 
 expect(window.sessionStorage.getItem('elvir_role')).toBeNull(); 
 expect(window.sessionStorage.getItem('elvir_token')).toBeNull(); 
 expect(service.isLoggedIn()).toBeFalse(); 
 });
});
