import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot } from '@angular/router';
import { AuthService } from '@core/services/auth.service';
import { authGuard } from '@core/guards/auth.guard';
import { guestGuard } from '@core/guards/guest.guard';
import { createRoleGuard } from '@core/guards/role.guard';
import { redirectToDashboardGuard } from '@core/guards/redirect-dashboard.guard';
import { interviewLeaveGuard } from '@core/guards/interview-leave.guard';

describe('Route guards', () => {
  let authStub: jasmine.SpyObj<AuthService>;
  let routerStub: jasmine.SpyObj<Router>;

  beforeEach(() => {
    authStub = jasmine.createSpyObj<AuthService>('AuthService', ['isLoggedIn', 'getRole']);
    routerStub = jasmine.createSpyObj<Router>('Router', ['navigate', 'createUrlTree']);

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: authStub },
        { provide: Router, useValue: routerStub },
      ],
    });
  });

  const dummyRoute = {} as ActivatedRouteSnapshot;
  const dummyState = {} as RouterStateSnapshot;
  const runGuard = <T>(guard: () => T): T => TestBed.runInInjectionContext(guard);

  it('authGuard redirects to /login when not logged in', () => {
    authStub.isLoggedIn.and.returnValue(false);

    const result = runGuard(() => authGuard(dummyRoute, dummyState));

    expect(result).toBeFalse();
    expect(routerStub.navigate).toHaveBeenCalledWith(['/login']);
  });

  it('authGuard allows navigation when logged in', () => {
    authStub.isLoggedIn.and.returnValue(true);

    const result = runGuard(() => authGuard(dummyRoute, dummyState));

    expect(result).toBeTrue();
    expect(routerStub.navigate).not.toHaveBeenCalled();
  });

  it('guestGuard allows navigation when not logged in', () => {
    authStub.isLoggedIn.and.returnValue(false);

    const result = runGuard(() => guestGuard(dummyRoute, dummyState));

    expect(result).toBeTrue();
    expect(routerStub.navigate).not.toHaveBeenCalled();
  });

  it('guestGuard redirects logged users based on role', () => {
    authStub.isLoggedIn.and.returnValue(true);

    authStub.getRole.and.returnValue('JOVEN');
    expect(runGuard(() => guestGuard(dummyRoute, dummyState))).toBeFalse();
    expect(routerStub.navigate).toHaveBeenCalledWith(['/joven/simulacion/nueva']);

    routerStub.navigate.calls.reset();
    authStub.getRole.and.returnValue('ADMIN');
    expect(runGuard(() => guestGuard(dummyRoute, dummyState))).toBeFalse();
    expect(routerStub.navigate).toHaveBeenCalledWith(['/admin/dashboard']);

    routerStub.navigate.calls.reset();
    authStub.getRole.and.returnValue('PROFESIONAL');
    expect(runGuard(() => guestGuard(dummyRoute, dummyState))).toBeFalse();
    expect(routerStub.navigate).toHaveBeenCalledWith(['/profesional/dashboard']);
  });

  it('role guard redirects when not logged in', () => {
    authStub.isLoggedIn.and.returnValue(false);

    const result = runGuard(() => createRoleGuard('JOVEN')(dummyRoute, dummyState));

    expect(result).toBeFalse();
    expect(routerStub.navigate).toHaveBeenCalledWith(['/login']);
  });

  it('role guard redirects to dashboard when role mismatches', () => {
    authStub.isLoggedIn.and.returnValue(true);
    authStub.getRole.and.returnValue('ADMIN');

    const result = runGuard(() => createRoleGuard('JOVEN')(dummyRoute, dummyState));

    expect(result).toBeFalse();
    expect(routerStub.navigate).toHaveBeenCalledWith(['/admin/dashboard']);
  });

  it('role guard allows navigation when role matches', () => {
    authStub.isLoggedIn.and.returnValue(true);
    authStub.getRole.and.returnValue('JOVEN');

    const result = runGuard(() => createRoleGuard('JOVEN')(dummyRoute, dummyState));

    expect(result).toBeTrue();
    expect(routerStub.navigate).not.toHaveBeenCalled();
  });

  it('redirectToDashboardGuard returns a UrlTree for the role', () => {
    const tree = { id: 'tree' } as unknown as ReturnType<Router['createUrlTree']>;
    routerStub.createUrlTree.and.returnValue(tree);
    authStub.getRole.and.returnValue('ADMIN');

    const result = runGuard(() => redirectToDashboardGuard(dummyRoute, dummyState));

    expect(routerStub.createUrlTree).toHaveBeenCalledWith(['/admin/dashboard']);
    expect(result).toBe(tree);
  });

  it('interviewLeaveGuard delegates to component canDeactivate', () => {
    const component = { canDeactivate: () => false } as unknown as { canDeactivate: () => boolean };

    const result = interviewLeaveGuard(component as never, dummyRoute, dummyState, dummyState);

    expect(result).toBeFalse();
  });
});
