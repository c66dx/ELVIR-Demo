import type { SessionStatus } from '@core/models/types.model';
import { SessionEndService } from '@core/services/session-end.service';

describe('SessionEndService', () => {
  it('stores, returns and clears session end data', () => {
    const service = new SessionEndService();
    const data = { status: 'COMPLETADA' as SessionStatus, motivo: 'ok', returnUrl: '/joven' };

    service.set(data);
    expect(service.get()).toEqual(data);

    service.clear();
    expect(service.get()).toBeNull();
  });
});
