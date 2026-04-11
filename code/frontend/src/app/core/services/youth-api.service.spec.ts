import { HttpHeaders } from '@angular/common/http';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { YouthApiService } from '@core/services/youth-api.service';
import { API_BASE } from '@core/services/api-http-helpers';

const buildHeaders = (values: Record<string, string>) => new HttpHeaders(values);

describe('YouthApiService', () => {
  let service: YouthApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), YouthApiService],
    });
    service = TestBed.inject(YouthApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('uploads youth photo and maps response', () => {
    let result: unknown;
    const file = new File(['demo'], 'photo.jpg', { type: 'image/jpeg' });
    service.uploadYouthPhoto('4', file).subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/youths/4/photo`);
    expect(req.request.body instanceof FormData).toBeTrue();
    req.flush({ id: 4, display_name: 'Ana', login_enabled: true, is_active: true });

    expect(result).toEqual(jasmine.objectContaining({ id: '4', display_name: 'Ana' }));
  });

  it('returns error when upload youth photo fails', () => {
    let result: unknown;
    const file = new File(['demo'], 'photo.jpg', { type: 'image/jpeg' });
    service.uploadYouthPhoto('4', file).subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/youths/4/photo`);
    req.flush(
      { detail: 'fail' },
      { status: 400, statusText: 'Bad', headers: buildHeaders({ 'X-Request-ID': 'req-1' }) }
    );

    const err = (result as { error: string }).error;
    expect(err).toContain('fail');
    expect(err).toContain('req-1');
  });

  it('lists youths with last session and query params', () => {
    let result: unknown;
    service.getYouths({ search: ' ana ', is_active: true, login_enabled: false }).subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/youths?search=ana&is_active=true&login_enabled=false`);
    req.flush([
      {
        id: 1,
        display_name: 'Ana',
        last_session: { id: 2, status: 'COMPLETADA', started_at: '2024-01-01' },
      },
    ]);

    const list = result as { id: string; last_session?: { id: string } }[];
    expect(list[0].id).toBe('1');
    expect(list[0].last_session?.id).toBe('2');
  });

  it('paginates youths and handles error', () => {
    let okResult: unknown;
    service.getYouthsPaged({ page: 2, page_size: 1 }).subscribe((value) => (okResult = value));

    const req = httpMock.expectOne(`${API_BASE}/youths?page=2&page_size=1`);
    req.flush([
      { id: 9, display_name: 'Pedro', login_enabled: false, is_active: true },
    ], {
      headers: buildHeaders({ 'X-Total-Count': '10', 'X-Page': '2', 'X-Page-Size': '1' }),
    });

    expect(okResult).toEqual({
      items: [jasmine.objectContaining({ id: '9' })],
      total: 10,
      page: 2,
      page_size: 1,
    });

    let errResult: unknown;
    service.getYouthsPaged({ page: 1, page_size: 5 }).subscribe((value) => (errResult = value));
    const errReq = httpMock.expectOne(`${API_BASE}/youths?page=1&page_size=5`);
    errReq.flush({ detail: 'fail' }, { status: 500, statusText: 'Error' });

    expect(errResult).toEqual({ items: [], total: 0, page: 1, page_size: 5 });
  });

  it('looks up youths and filters ids', () => {
    let result: unknown;
    service.getYouthLookup(['1', 'x', '2']).subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/youths/lookup`);
    expect(req.request.body).toEqual({ ids: [1, 2] });
    req.flush([{ id: 1, display_name: 'Ana' }]);

    expect(result).toEqual([jasmine.objectContaining({ id: '1', display_name: 'Ana' })]);
  });

  it('creates youth and includes email when provided', () => {
    let result: unknown;
    service
      .createYouth({
        display_name: 'Ana',
        rut: '1-9',
        phone: '123',
        year_of_birth: 2000,
        diagnosis: 'Ok',
        login_enabled: true,
        is_active: true,
        general_notes: 'Notes',
        profile_checklist: ['a'],
        email: 'ana@demo.cl',
      })
      .subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/youths`);
    expect(req.request.body).toEqual(jasmine.objectContaining({ email: 'ana@demo.cl' }));
    req.flush({ id: 3, display_name: 'Ana', login_enabled: true, is_active: true, activation_url: 'http://act' });

    expect(result).toEqual(jasmine.objectContaining({ id: '3', activation_url: 'http://act' }));
  });

  it('gets a youth and returns null on error', () => {
    let okResult: unknown;
    service.getYouth('5').subscribe((value) => (okResult = value));

    const req = httpMock.expectOne(`${API_BASE}/youths/5`);
    req.flush({ id: 5, display_name: 'Sol', login_enabled: false, is_active: true });
    expect(okResult).toEqual(jasmine.objectContaining({ id: '5', display_name: 'Sol' }));

    let errResult: unknown;
    service.getYouth('6').subscribe((value) => (errResult = value));
    const errReq = httpMock.expectOne(`${API_BASE}/youths/6`);
    errReq.flush({ detail: 'fail' }, { status: 404, statusText: 'Not Found' });
    expect(errResult).toBeNull();
  });

  it('updates youth and strips identifier', () => {
    let result: unknown;
    service.updateYouth('7', { display_name: 'Neo', identifier: 'abc' } as never).subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/youths/7`);
    expect(req.request.body).toEqual({ display_name: 'Neo' });
    req.flush({ id: 7, display_name: 'Neo', login_enabled: true, is_active: true });

    expect(result).toEqual(jasmine.objectContaining({ id: '7', display_name: 'Neo' }));
  });

  it('deactivates and activates youth', () => {
    service.deactivateYouth('8').subscribe();
    const deactivateReq = httpMock.expectOne(`${API_BASE}/youths/8/deactivate`);
    expect(deactivateReq.request.method).toBe('PATCH');
    deactivateReq.flush({});

    service.activateYouth('8').subscribe();
    const activateReq = httpMock.expectOne(`${API_BASE}/youths/8/activate`);
    expect(activateReq.request.method).toBe('PATCH');
    activateReq.flush({});
  });

  it('changes youth email and handles error', () => {
    let okResult: unknown;
    service.changeYouthEmail('9', 'new@demo.cl').subscribe((value) => (okResult = value));

    const req = httpMock.expectOne(`${API_BASE}/youths/9/change-email`);
    expect(req.request.body).toEqual({ new_email: 'new@demo.cl' });
    req.flush({ id: 9, display_name: 'Ana', login_enabled: true, is_active: true, email: 'new@demo.cl' });

    expect(okResult).toEqual(jasmine.objectContaining({ id: '9', email: 'new@demo.cl' }));

    let errResult: unknown;
    service.changeYouthEmail('9', 'bad@demo.cl').subscribe((value) => (errResult = value));
    const errReq = httpMock.expectOne(`${API_BASE}/youths/9/change-email`);
    errReq.flush({ detail: 'fail' }, { status: 400, statusText: 'Bad' });

    expect(errResult).toBeNull();
  });
});
