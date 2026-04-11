import { str, withRequestId } from '@core/services/api-http-helpers';

describe('api-http-helpers', () => {
  it('converts ids to strings', () => {
    expect(str(42)).toBe('42');
    expect(str('7')).toBe('7');
    expect(str(null)).toBe('');
    expect(str(undefined)).toBe('');
  });

  it('appends request id when present', () => {
    const errWithId = {
      headers: {
        get: (name: string) => (name === 'X-Request-ID' ? 'req-123' : null),
      },
    };
    const result = withRequestId('Boom', errWithId);
    expect(result).toContain('Boom');
    expect(result).toContain('req-123');

    const errWithoutId = { headers: { get: () => null } };
    expect(withRequestId('Boom', errWithoutId)).toBe('Boom');
  });
});
