import { HttpHeaders } from '@angular/common/http';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthApiService } from '@core/services/auth-api.service';
import { API_BASE } from '@core/services/api-http-helpers';

describe('AuthApiService', () => {
  let service: AuthApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), AuthApiService],
    });
    service = TestBed.inject(AuthApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('maps login response', () => {
    let result: unknown;
    service.login('me@demo.cl', 'secret').subscribe((res) => (result = res));

    const req = httpMock.expectOne(`${API_BASE}/auth/login`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ email: 'me@demo.cl', password: 'secret' });

    req.flush({ access_token: 'tok', role: 'JOVEN', user_id: 5 });

    expect(result).toEqual({ access_token: 'tok', role: 'JOVEN', user_id: '5' });
  });

  it('handles login errors with request id', () => {
    let result: unknown;
    service.login('me@demo.cl', 'bad').subscribe((res) => (result = res));

    const req = httpMock.expectOne(`${API_BASE}/auth/login`);
    req.flush(
      { detail: 'Credenciales invalidas' },
      { status: 401, statusText: 'Unauthorized', headers: new HttpHeaders({ 'X-Request-ID': 'req-1' }) }
    );

    const error = (result as { error: string }).error;
    expect(error).toContain('Credenciales');
    expect(error).toContain('req-1');
  });

  it('handles login errors with array detail', () => {
    let result: unknown;
    service.login('me@demo.cl', 'bad').subscribe((res) => (result = res));

    const req = httpMock.expectOne(`${API_BASE}/auth/login`);
    req.flush({ detail: [{ msg: 'Nope' }] }, { status: 400, statusText: 'Bad Request' });

    expect((result as { error: string }).error).toContain('Nope');
  });

  it('logs out even when backend fails', () => {
    let value: unknown;
    service.logout().subscribe((res) => (value = res));

    const req = httpMock.expectOne(`${API_BASE}/auth/logout`);
    expect(req.request.method).toBe('POST');

    req.flush({ detail: 'fail' }, { status: 500, statusText: 'Error' });

    expect(value).toBeUndefined();
  });

  it('maps getMe response', () => {
    let result: unknown;
    service.getMe().subscribe((res) => (result = res));

    const req = httpMock.expectOne(`${API_BASE}/auth/me`);
    req.flush({
      user_id: 1,
      role: 'PROFESIONAL',
      email: 'me@demo.cl',
      profile_photo_url: null,
      professional_id: 7,
      youth_id: null,
    });

    expect(result).toEqual({
      user_id: '1',
      role: 'PROFESIONAL',
      email: 'me@demo.cl',
      profile_photo_url: undefined,
      professional_id: '7',
      youth_id: undefined,
    });
  });

  it('returns null when getMe fails', () => {
    let result: unknown;
    service.getMe().subscribe((res) => (result = res));

    const req = httpMock.expectOne(`${API_BASE}/auth/me`);
    req.flush({ detail: 'boom' }, { status: 500, statusText: 'Error' });

    expect(result).toBeNull();
  });

  it('changes password and handles error detail', () => {
    let successResult: unknown;
    service.changePassword('old', 'new').subscribe((res) => (successResult = res));

    const okReq = httpMock.expectOne(`${API_BASE}/auth/change-password`);
    expect(okReq.request.body).toEqual({ current_password: 'old', new_password: 'new' });
    okReq.flush({ success: true });
    expect(successResult).toEqual({ success: true });

    let errorResult: unknown;
    service.changePassword('old', 'bad').subscribe((res) => (errorResult = res));
    const errReq = httpMock.expectOne(`${API_BASE}/auth/change-password`);
    errReq.flush(
      { detail: 'Invalid' },
      { status: 400, statusText: 'Bad', headers: new HttpHeaders({ 'X-Request-ID': 'req-2' }) }
    );

    const err = (errorResult as { error: string }).error;
    expect(err).toContain('Invalid');
    expect(err).toContain('req-2');
  });

  it('requests email change', () => {
    let result: unknown;
    service.requestEmailChange('new@demo.cl', 'pw').subscribe((res) => (result = res));

    const req = httpMock.expectOne(`${API_BASE}/auth/change-email`);
    expect(req.request.body).toEqual({ new_email: 'new@demo.cl', current_password: 'pw' });
    req.flush({ success: true, activation_url: 'http://activate' });

    expect(result).toEqual({ success: true, activation_url: 'http://activate' });
  });

  it('uploads profile photo', () => {
    let result: unknown;
    const file = new File(['demo'], 'photo.jpg', { type: 'image/jpeg' });
    service.uploadProfilePhoto(file).subscribe((res) => (result = res));

    const req = httpMock.expectOne(`${API_BASE}/auth/me/photo`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body instanceof FormData).toBeTrue();
    req.flush({ url: 'http://cdn/photo.jpg' });

    expect(result).toEqual({ url: 'http://cdn/photo.jpg' });
  });

  it('validates activation token and handles error', () => {
    let okResult: unknown;
    service.validateActivationToken('tok').subscribe((res) => (okResult = res));
    const okReq = httpMock.expectOne(`${API_BASE}/auth/activate/validate?token=tok`);
    okReq.flush({ valid: true, email: 'a@b.c', display_name: 'Ana', is_change_email: true });
    expect(okResult).toEqual({ valid: true, email: 'a@b.c', display_name: 'Ana', is_change_email: true });

    let errResult: unknown;
    service.validateActivationToken('bad').subscribe((res) => (errResult = res));
    const errReq = httpMock.expectOne(`${API_BASE}/auth/activate/validate?token=bad`);
    errReq.flush({ detail: 'err' }, { status: 404, statusText: 'Not Found' });
    expect(errResult).toEqual({ valid: false, error: 'TOKEN_NOT_FOUND' });
  });

  it('activates account and handles backend error', () => {
    let okResult: unknown;
    service.activateAccount({ token: 'tok', password: 'pw' }).subscribe((res) => (okResult = res));
    const okReq = httpMock.expectOne(`${API_BASE}/auth/activate`);
    expect(okReq.request.body).toEqual({ token: 'tok', password: 'pw' });
    okReq.flush({ success: true, error: null });
    expect(okResult).toEqual({ success: true, error: null });

    let errResult: unknown;
    service.activateAccount({ token: 'tok' }).subscribe((res) => (errResult = res));
    const errReq = httpMock.expectOne(`${API_BASE}/auth/activate`);
    errReq.flush(
      { error: 'TOKEN_BAD' },
      { status: 400, statusText: 'Bad', headers: new HttpHeaders({ 'X-Request-ID': 'req-3' }) }
    );

    const err = (errResult as { success: boolean; error: string }).error;
    expect(err).toContain('TOKEN_BAD');
    expect(err).toContain('req-3');
  });

  it('swallows upload photo errors', () => {
    let result: unknown;
    const file = new File(['demo'], 'photo.jpg', { type: 'image/jpeg' });
    service.uploadProfilePhoto(file).subscribe((res) => (result = res));

    const req = httpMock.expectOne(`${API_BASE}/auth/me/photo`);
    req.flush(
      { detail: 'fail' },
      { status: 400, statusText: 'Bad', headers: new HttpHeaders({ 'X-Request-ID': 'req-4' }) }
    );

    const err = (result as { error: string }).error;
    expect(err).toContain('fail');
    expect(err).toContain('req-4');
  });

  it('handles request email change errors', () => {
    let result: unknown;
    service.requestEmailChange('new@demo.cl', 'pw').subscribe((res) => (result = res));

    const req = httpMock.expectOne(`${API_BASE}/auth/change-email`);
    req.flush(
      { detail: 'bad' },
      { status: 400, statusText: 'Bad', headers: new HttpHeaders({ 'X-Request-ID': 'req-5' }) }
    );

    const err = (result as { error: string }).error;
    expect(err).toContain('bad');
    expect(err).toContain('req-5');
  });

});
