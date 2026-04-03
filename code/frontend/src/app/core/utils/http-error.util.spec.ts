import { HttpErrorResponse } from '@angular/common/http';

import { extractErrorMessage } from './http-error.util';

describe('extractErrorMessage', () => {
  it('prioriza detail string en 429', () => {
    const err = new HttpErrorResponse({
      status: 429,
      error: { detail: 'Demasiadas solicitudes. 5 per minute' },
    });
    expect(extractErrorMessage(err)).toBe('Demasiadas solicitudes. 5 per minute');
  });

  it('429 sin detail usa error.error.message', () => {
    const err = new HttpErrorResponse({
      status: 429,
      error: { error: { message: 'Límite alcanzado' } },
    });
    expect(extractErrorMessage(err)).toBe('Límite alcanzado');
  });

  it('429 sin cuerpo útil usa mensaje genérico', () => {
    const err = new HttpErrorResponse({
      status: 429,
      error: {},
    });
    expect(extractErrorMessage(err)).toContain('Demasiadas solicitudes');
  });

  it('añade request id al final cuando se pasa', () => {
    const err = new HttpErrorResponse({
      status: 429,
      error: { detail: 'Demasiadas solicitudes. x' },
    });
    expect(extractErrorMessage(err, 'req-abc')).toContain('req-abc');
  });
});
