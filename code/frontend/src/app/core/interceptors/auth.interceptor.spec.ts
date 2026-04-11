import { HttpClient, HttpHeaders } from '@angular/common/http';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { AuthService } from '@core/services/auth.service';
import { authInterceptor } from '@core/interceptors/auth.interceptor';

const CSRF_COOKIE_NAME = 'elvir_csrf_token';

const setCookie = (name: string, value: string): void => {
  document.cookie = `${name}=${value}; path=/`;
};

const clearCookie = (name: string): void => {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
};

const swallowError = (err: unknown): void => {
  void err;
};

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let authStub: jasmine.SpyObj<AuthService>;
  let routerStub: jasmine.SpyObj<Router>;

  beforeEach(() => {
    authStub = jasmine.createSpyObj<AuthService>('AuthService', ['getToken', 'logout']);
    routerStub = jasmine.createSpyObj<Router>('Router', ['navigate']);

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authStub },
        { provide: Router, useValue: routerStub },
      ],
    });

    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    clearCookie(CSRF_COOKIE_NAME);
  });

  it('adds auth, csrf, and request id headers', () => {
    authStub.getToken.and.returnValue('token-123');
    setCookie(CSRF_COOKIE_NAME, 'csrf-xyz');

    http.post('/api/demo', { ok: true }).subscribe();

    const req = httpMock.expectOne('/api/demo');
    expect(req.request.headers.get('Authorization')).toBe('Bearer token-123');
    expect(req.request.headers.get('X-CSRF-Token')).toBe('csrf-xyz');
    expect(req.request.headers.has('X-Request-ID')).toBeTrue();
    expect(req.request.withCredentials).toBeFalse();

    req.flush({});
  });

  it('preserves an existing request id header', () => {
    http
      .get('/api/with-id', { headers: new HttpHeaders({ 'X-Request-ID': 'req-abc' }) })
      .subscribe();

    const req = httpMock.expectOne('/api/with-id');
    expect(req.request.headers.get('X-Request-ID')).toBe('req-abc');
    req.flush({});
  });

  it('logs out and redirects on 401 for non-auth endpoints', () => {
    http.get('/api/secure').subscribe({ error: swallowError });

    const req = httpMock.expectOne('/api/secure');
    req.flush({ detail: 'unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    expect(authStub.logout).toHaveBeenCalled();
    expect(routerStub.navigate).toHaveBeenCalledWith(['/login']);
  });

  it('does not redirect on auth endpoints', () => {
    http.post('/auth/login', { email: 'a@b.c', password: 'x' }).subscribe({ error: swallowError });

    const req = httpMock.expectOne('/auth/login');
    req.flush({ detail: 'invalid' }, { status: 401, statusText: 'Unauthorized' });

    expect(authStub.logout).not.toHaveBeenCalled();
    expect(routerStub.navigate).not.toHaveBeenCalled();
  });
});
