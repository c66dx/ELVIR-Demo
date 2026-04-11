import { HttpEventType, HttpHeaders } from '@angular/common/http';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { MaterialApiService } from '@core/services/material-api.service';
import { API_BASE } from '@core/services/api-http-helpers';

const buildHeaders = (values: Record<string, string>) => new HttpHeaders(values);

describe('MaterialApiService', () => {
  let service: MaterialApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), MaterialApiService],
    });
    service = TestBed.inject(MaterialApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('uploads files and emits progress plus url', () => {
    const file = new File(['demo'], 'demo.pdf', { type: 'application/pdf' });
    const emitted: { progress?: number; url?: string; error?: string }[] = [];
    service.uploadFile(file).subscribe((value) => emitted.push(value));

    const req = httpMock.expectOne(`${API_BASE}/upload`);
    expect(req.request.reportProgress).toBeTrue();
    expect(req.request.body instanceof FormData).toBeTrue();

    req.event({ type: HttpEventType.UploadProgress, loaded: 50, total: 100 });
    req.event({ type: HttpEventType.UploadProgress, loaded: 5 });
    req.flush({ url: 'http://cdn/file.pdf' });

    expect(emitted).toEqual([{ progress: 50 }, { progress: -1 }, { url: 'http://cdn/file.pdf' }]);
  });

  it('returns upload error with request id', () => {
    const file = new File(['demo'], 'demo.pdf', { type: 'application/pdf' });
    let result: unknown;
    service.uploadFile(file).subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/upload`);
    req.flush(
      { detail: 'fail' },
      { status: 400, statusText: 'Bad', headers: buildHeaders({ 'X-Request-ID': 'req-1' }) }
    );

    const error = (result as { error: string }).error;
    expect(error).toContain('fail');
    expect(error).toContain('req-1');
  });

  it('creates support material and maps ids', () => {
    let result: unknown;
    service
      .createSupportMaterial({
        title: 'Video',
        description: 'Desc',
        type: 'VIDEO',
        url: 'http://video',
        job_role_id: '3',
        case_id: '5',
      })
      .subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/support-material`);
    expect(req.request.body).toEqual({
      title: 'Video',
      description: 'Desc',
      type: 'VIDEO',
      url: 'http://video',
      job_role_id: 3,
      case_id: 5,
    });

    req.flush({ id: 11, title: 'Video', description: 'Desc', type: 'VIDEO', url: 'http://video', job_role_id: 3, case_id: 5 });

    expect(result).toEqual(
      jasmine.objectContaining({ id: '11', job_role_id: '3', case_id: '5', active: true })
    );
  });

  it('returns error when create support material fails', () => {
    let result: unknown;
    service
      .createSupportMaterial({ title: 'Video', type: 'VIDEO', url: 'http://video' })
      .subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/support-material`);
    req.flush(
      { detail: 'bad' },
      { status: 400, statusText: 'Bad', headers: buildHeaders({ 'X-Request-ID': 'req-2' }) }
    );

    const error = (result as { error: string }).error;
    expect(error).toContain('bad');
    expect(error).toContain('req-2');
  });

  it('paginates support material with headers', () => {
    let result: unknown;
    service.getSupportMaterialPaged({ page: 2, page_size: 5 }).subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/support-material?page=2&page_size=5`);
    req.flush(
      [{ id: 1, title: 'Doc', type: 'PDF', url: 'u' }],
      { headers: buildHeaders({ 'X-Total-Count': '10', 'X-Page': '2', 'X-Page-Size': '5' }) }
    );

    expect(result).toEqual({
      items: [jasmine.objectContaining({ id: '1', type: 'PDF' })],
      total: 10,
      page: 2,
      page_size: 5,
    });
  });

  it('returns empty page on support material error', () => {
    let result: unknown;
    service.getSupportMaterialPaged({ page: 1, page_size: 5 }).subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/support-material?page=1&page_size=5`);
    req.flush({ detail: 'fail' }, { status: 500, statusText: 'Error' });

    expect(result).toEqual({ items: [], total: 0, page: 1, page_size: 5 });
  });

  it('maps youth material suggestions with material details', () => {
    let result: unknown;
    service.getYouthMaterialSuggestionsPaged('12', { page: 1, page_size: 2 }).subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/youths/12/material-suggestions?page=1&page_size=2`);
    req.flush(
      [
        {
          id: 1,
          material_id: 7,
          professional_id: 4,
          material: { id: 7, title: 'Doc', type: 'PDF', url: 'u' },
        },
      ],
      { headers: buildHeaders({ 'X-Total-Count': '1', 'X-Page': '1', 'X-Page-Size': '2' }) }
    );

    const paged = result as { items: { material?: { id: string } | null }[] };
    expect(paged.items[0].material).toEqual(jasmine.objectContaining({ id: '7' }));
  });

  it('maps youth material views and notifications', () => {
    let viewsResult: unknown;
    service.getYouthMaterialViewsPaged('9', { page: 1, page_size: 1 }).subscribe((value) => (viewsResult = value));

    const viewsReq = httpMock.expectOne(`${API_BASE}/youths/9/material-views?page=1&page_size=1`);
    viewsReq.flush(
      [{ id: 3, youth_id: 9, material_id: 5, seen_at: '2024-01-01' }],
      { headers: buildHeaders({ 'X-Total-Count': '1', 'X-Page': '1', 'X-Page-Size': '1' }) }
    );

    expect(viewsResult).toEqual({
      items: [jasmine.objectContaining({ id: '3', material_id: '5' })],
      total: 1,
      page: 1,
      page_size: 1,
    });

    let notificationsResult: unknown;
    service.getYouthNotificationsPaged('9', { page: 1, page_size: 2, unread_only: true }).subscribe((value) => (notificationsResult = value));

    const notifReq = httpMock.expectOne(`${API_BASE}/youths/9/notifications?page=1&page_size=2&unread_only=true`);
    notifReq.flush(
      [{ id: 1, youth_id: 9, type: 'material', title: 'Hi', message: 'Msg', created_at: '2024-01-01' }],
      { headers: buildHeaders({ 'X-Total-Count': '1', 'X-Total-Unread': '1', 'X-Page': '1', 'X-Page-Size': '2' }) }
    );

    expect(notificationsResult).toEqual({
      items: [jasmine.objectContaining({ id: '1', type: 'material' })],
      total: 1,
      unread: 1,
      page: 1,
      page_size: 2,
    });
  });

  it('marks notifications read and handles errors', () => {
    let result: unknown;
    service.markYouthNotificationsRead('10', ['1', 'x']).subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/youths/10/notifications/read`);
    expect(req.request.body).toEqual({ ids: [1] });
    req.flush({ updated: 2 });
    expect(result).toEqual({ updated: 2 });

    let errResult: unknown;
    service.markAllYouthNotificationsRead('10').subscribe((value) => (errResult = value));
    const errReq = httpMock.expectOne(`${API_BASE}/youths/10/notifications/read-all`);
    errReq.flush({ detail: 'fail' }, { status: 500, statusText: 'Error' });
    expect(errResult).toEqual({ updated: 0 });
  });

  it('records material view', () => {
    let result: unknown;
    service.recordMaterialView('3', '8').subscribe((value) => (result = value));

    const req = httpMock.expectOne(`${API_BASE}/support-material/3/view`);
    expect(req.request.body).toEqual({ youth_id: 8 });
    req.flush({ id: 9, youth_id: 8, material_id: 3, seen_at: '2024-01-02' });

    expect(result).toEqual(jasmine.objectContaining({ id: '9', youth_id: '8', material_id: '3' }));
  });
});
