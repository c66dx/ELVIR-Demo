import { TestBed } from '@angular/core/testing';
import { firstValueFrom, of } from 'rxjs';

import { AuthApiService } from '@core/services/auth-api.service';
import { YouthApiService } from '@core/services/youth-api.service';
import type { PagedResult, YouthWithLastSession } from '@core/services/api-types';
import { YouthService } from '@core/services/youth.service';

describe('YouthService', () => {
  let service: YouthService;
  let authApiStub: jasmine.SpyObj<AuthApiService>;
  let youthApiStub: jasmine.SpyObj<YouthApiService>;

  beforeEach(() => {
    authApiStub = jasmine.createSpyObj<AuthApiService>('AuthApiService', ['getMe']);
    youthApiStub = jasmine.createSpyObj<YouthApiService>('YouthApiService', ['getYouthsPaged']);
    TestBed.configureTestingModule({
      providers: [
        YouthService,
        { provide: AuthApiService, useValue: authApiStub },
        { provide: YouthApiService, useValue: youthApiStub },
      ],
    });
    service = TestBed.inject(YouthService);
  });

  it('returns null when there is no session or role is not JOVEN', async () => {
    authApiStub.getMe.and.returnValue(of(null));

    const result = await firstValueFrom(service.getCurrentYouthId());

    expect(result).toBeNull();
    expect(youthApiStub.getYouthsPaged).not.toHaveBeenCalled();
  });

  it('returns youth_id when available', async () => {
    authApiStub.getMe.and.returnValue(
      of({ role: 'JOVEN', youth_id: 42, user_id: '1', email: 'me@demo.cl' } as never)
    );

    const result = await firstValueFrom(service.getCurrentYouthId());

    expect(result).toBe('42');
    expect(youthApiStub.getYouthsPaged).not.toHaveBeenCalled();
  });

  it('falls back to first youth from list when youth_id is missing', async () => {
    authApiStub.getMe.and.returnValue(of({ role: 'JOVEN', user_id: '1', email: 'me@demo.cl' } as never));
    const paged: PagedResult<YouthWithLastSession> = {
      items: [{ id: '99' } as YouthWithLastSession],
      total: 1,
      page: 1,
      page_size: 1,
    };
    youthApiStub.getYouthsPaged.and.returnValue(of(paged));

    const result = await firstValueFrom(service.getCurrentYouthId());

    expect(youthApiStub.getYouthsPaged).toHaveBeenCalledWith({ page: 1, page_size: 1 });
    expect(result).toBe('99');
  });

  it('returns null when no youths are available', async () => {
    authApiStub.getMe.and.returnValue(of({ role: 'JOVEN', user_id: '1', email: 'me@demo.cl' } as never));
    const paged: PagedResult<YouthWithLastSession> = {
      items: [],
      total: 0,
      page: 1,
      page_size: 1,
    };
    youthApiStub.getYouthsPaged.and.returnValue(of(paged));

    const result = await firstValueFrom(service.getCurrentYouthId());

    expect(result).toBeNull();
  });
});
