import { HttpClient, HttpHeaders } from '@angular/common/http';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { NotificationService } from '@core/services/notification.service';
import { errorInterceptor } from '@core/interceptors/error.interceptor';

const swallowError = (err: unknown): void => {
  void err;
};

describe('errorInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let notificationStub: jasmine.SpyObj<NotificationService>;

  beforeEach(() => {
    notificationStub = jasmine.createSpyObj<NotificationService>('NotificationService', ['error']);

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([errorInterceptor])),
        provideHttpClientTesting(),
        { provide: NotificationService, useValue: notificationStub },
      ],
    });

    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('notifies on non-skipped URLs', () => {
    http.get('/api/some-endpoint').subscribe({ error: swallowError });

    const req = httpMock.expectOne('/api/some-endpoint');
    req.flush(
      { detail: 'boom' },
      {
        status: 500,
        statusText: 'Server Error',
        headers: new HttpHeaders({ 'X-Request-ID': 'req-123' }),
      }
    );

    expect(notificationStub.error).toHaveBeenCalled();
    const message = notificationStub.error.calls.mostRecent().args[0];
    expect(message).toContain('req-123');
  });

  it('skips toast for auth URLs', () => {
    http.post('/auth/login', { email: 'a@b.c', password: 'x' }).subscribe({ error: swallowError });

    const req = httpMock.expectOne('/auth/login');
    req.flush({ detail: 'invalid' }, { status: 401, statusText: 'Unauthorized' });

    expect(notificationStub.error).not.toHaveBeenCalled();
  });

  it('skips toast for session audio upload URLs', () => {
    http.post('/sessions/abc/audio', new Blob()).subscribe({ error: swallowError });

    const req = httpMock.expectOne('/sessions/abc/audio');
    req.flush({ detail: 'boom' }, { status: 500, statusText: 'Server Error' });

    expect(notificationStub.error).not.toHaveBeenCalled();
  });
});
