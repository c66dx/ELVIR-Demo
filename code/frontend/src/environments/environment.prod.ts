/**
 * Build de producción (demo). URL absoluta del API + credenciales alineadas con seed.py.
 */
export const environment = {
  production: true,
  apiUrl: 'https://p01--elvir-backend--gdvh5qbny2m8.code.run/api/v1',
  /** Producción: alineado con `PASSWORD_MIN_LENGTH` = 12 en el backend cuando `ENV=prod`. */
  passwordMinLength: 12,
  demoCredentials: {
    joven: 'elvir.demo+joven1@gmail.com',
    tutor: 'prof@test.cl',
    admin: 'admin@test.cl',
    password: 'test123',
    note: 'elvir.demo+joven2@gmail.com tiene el inicio de sesión deshabilitado.',
    more: 'Otros jóvenes de prueba: elvir.demo+joven3@gmail.com a elvir.demo+joven6@gmail.com (misma clave).',
  },
};
