import { take } from 'rxjs';

import { NotificationService } from '@core/services/notification.service';

describe('NotificationService', () => {
  let service: NotificationService;

  beforeEach(() => {
    service = new NotificationService();
  });

  it('emite toasts success con id incremental', (done) => {
    const seen: number[] = [];
    service.messages.pipe(take(2)).subscribe({
      complete: () => {
        expect(seen).toEqual([1, 2]);
        done();
      },
      next: (m) => seen.push(m.id),
    });
    service.success('ok');
    service.error('fail');
  });

  it('tipos success, error e info', (done) => {
    const types: string[] = [];
    service.messages.pipe(take(3)).subscribe({
      complete: () => {
        expect(types).toEqual(['success', 'error', 'info']);
        done();
      },
      next: (m) => types.push(m.type),
    });
    service.success('s');
    service.error('e');
    service.info('i');
  });
});
