/**
 * Build de producción. En main coincide con el seed mínimo (dos jóvenes @test.cl).
 * Otra rama (p. ej. preview) puede reemplazar este archivo con credenciales extendidas (Gmail, etc.).
 */
export const environment = {
  production: true,
  apiUrl: '/api/v1',
  demoCredentials: {
    joven: 'joven1@test.cl',
    tutor: 'prof@test.cl',
    admin: 'admin@test.cl',
    password: 'test123',
    note: 'joven2@test.cl tiene el inicio de sesión deshabilitado.',
    more: '',
  },
};
