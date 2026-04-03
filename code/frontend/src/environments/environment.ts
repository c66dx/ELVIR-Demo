/** Texto de ayuda en login; debe coincidir con `code/backend/seed.py` en la rama main. */
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1',
  /** Debe coincidir con `PASSWORD_MIN_LENGTH` del backend en este entorno (dev default 6). */
  passwordMinLength: 6,
  demoCredentials: {
    joven: 'joven1@test.cl',
    tutor: 'prof@test.cl',
    admin: 'admin@test.cl',
    password: 'test123',
    note: 'joven2@test.cl tiene el inicio de sesión deshabilitado.',
    more: '',
  },
};
