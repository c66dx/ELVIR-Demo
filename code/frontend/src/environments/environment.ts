/** Texto de ayuda en login; debe coincidir con `code/backend/seed.py` en la rama main. */
export const environment = {
  production: false,
  apiUrl: '/api/v1',
  /** Debe coincidir con `PASSWORD_MIN_LENGTH` del backend en este entorno (dev default 6). */
  passwordMinLength: 6,
  demoCredentials: {
    joven: 'elvir.demo+joven1@gmail.com',
    tutor: 'prof@test.cl',
    admin: 'admin@test.cl',
    password: 'test123',
    note: 'elvir.demo+joven2@gmail.com tiene el inicio de sesión deshabilitado.',
    more: 'Otros jóvenes de prueba: elvir.demo+joven3@gmail.com a elvir.demo+joven6@gmail.com (misma clave).',
  },
};
