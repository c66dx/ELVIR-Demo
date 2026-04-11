import { HttpErrorResponse } from '@angular/common/http';

import { extractErrorMessage } from '@core/utils/http-error.util';

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

  it('no HttpErrorResponse devuelve mensaje genérico', () => {
    expect(extractErrorMessage(new Error('x'))).toBe('Ha ocurrido un error');
    expect(extractErrorMessage(null)).toBe('Ha ocurrido un error');
  });

  it('detail string en otros códigos (p. ej. 400)', () => {
    const err = new HttpErrorResponse({
      status: 400,
      error: { detail: 'Campo requerido' },
    });
    expect(extractErrorMessage(err)).toBe('Campo requerido');
  });

  it('422 con detail array usa msg del primer ítem', () => {
    const err = new HttpErrorResponse({
      status: 422,
      error: {
        detail: [{ type: 'value_error', loc: ['body', 'email'], msg: 'Correo inválido' }],
      },
    });
    expect(extractErrorMessage(err)).toBe('Correo inválido');
  });

  it('422 con detail array usa message si no hay msg', () => {
    const err = new HttpErrorResponse({
      status: 422,
      error: { detail: [{ message: 'Solo message' }] },
    });
    expect(extractErrorMessage(err)).toBe('Solo message');
  });

  it('422 normaliza mensajes de email en inglés (Pydantic)', () => {
    const err = new HttpErrorResponse({
      status: 422,
      error: {
        detail: [{ msg: 'value is not a valid email address: not a valid email' }],
      },
    });
    expect(extractErrorMessage(err)).toBe('Introduce un correo electrónico válido.');
  });

  it('404 sin detail usa mensaje por estado', () => {
    const err = new HttpErrorResponse({
      status: 404,
      error: {},
    });
    expect(extractErrorMessage(err)).toBe('Recurso no encontrado');
  });

  it('estatus sin mapeo usa Error N', () => {
    const err = new HttpErrorResponse({
      status: 418,
      error: {},
    });
    expect(extractErrorMessage(err)).toBe('Error 418');
  });
});
