import { TestBed } from '@angular/core/testing';
import { firstValueFrom, of } from 'rxjs';

import { MaterialApiService } from '@core/services/material-api.service';
import type { YouthNotificationDto, YouthNotificationsPage } from '@core/services/api-types';
import { YouthNotificationsService } from '@core/services/youth-notifications.service';

describe('YouthNotificationsService', () => {
  let service: YouthNotificationsService;
  let materialApiStub: jasmine.SpyObj<MaterialApiService>;

  beforeEach(() => {
    materialApiStub = jasmine.createSpyObj<MaterialApiService>('MaterialApiService', [
      'getYouthNotificationsPaged',
      'markYouthNotificationsRead',
      'markAllYouthNotificationsRead',
    ]);
    TestBed.configureTestingModule({
      providers: [
        YouthNotificationsService,
        { provide: MaterialApiService, useValue: materialApiStub },
      ],
    });
    service = TestBed.inject(YouthNotificationsService);
  });

  it('maps notifications and computes relative time', async () => {
    const now = new Date('2024-01-01T00:00:30Z').getTime();
    spyOn(Date, 'now').and.returnValue(now);
    const items: YouthNotificationDto[] = [
      {
        id: 'n1',
        youth_id: 'y1',
        type: 'material',
        title: 'Hola',
        message: 'Mensaje',
        created_at: new Date(now - 30_000).toISOString(),
        read_at: null,
      },
    ];
    const paged: YouthNotificationsPage = {
      items,
      total: 1,
      page: 1,
      page_size: 10,
      unread: 1,
    };
    materialApiStub.getYouthNotificationsPaged.and.returnValue(of(paged));

    const result = await firstValueFrom(service.getYouthNotifications('y1'));

    expect(result.items[0]).toEqual(
      jasmine.objectContaining({
        id: 'n1',
        read: false,
        time: 'Hace un momento',
      })
    );
  });

  it('handles invalid dates and read_at flag', async () => {
    const items: YouthNotificationDto[] = [
      {
        id: 'n2',
        youth_id: 'y1',
        type: 'general',
        title: 'Aviso',
        message: 'Texto',
        created_at: 'invalid-date',
        read_at: '2024-01-01T00:00:00Z',
      },
    ];
    const paged: YouthNotificationsPage = {
      items,
      total: 1,
      page: 1,
      page_size: 10,
      unread: 0,
    };
    materialApiStub.getYouthNotificationsPaged.and.returnValue(of(paged));

    const result = await firstValueFrom(service.getYouthNotifications('y1'));

    expect(result.items[0].read).toBeTrue();
    expect(result.items[0].time).toBe('Reciente');
  });

  it('delegates markAsRead and markAllRead to MaterialApiService', async () => {
    materialApiStub.markYouthNotificationsRead.and.returnValue(of({ updated: 1 }));
    materialApiStub.markAllYouthNotificationsRead.and.returnValue(of({ updated: 4 }));

    await firstValueFrom(service.markAsRead('y1', 'n1'));
    await firstValueFrom(service.markAllRead('y1'));

    expect(materialApiStub.markYouthNotificationsRead).toHaveBeenCalledWith('y1', ['n1']);
    expect(materialApiStub.markAllYouthNotificationsRead).toHaveBeenCalledWith('y1');
  });
});
