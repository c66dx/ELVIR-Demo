/** Build de producción; mismas credenciales de demo que desarrollo y `seed.py`. */
export const environment = {
  production: true,
  apiUrl: '/api/v1',
  demoCredentials: {
    joven: 'elvir.demo+joven1@gmail.com',
    tutor: 'prof@test.cl',
    admin: 'admin@test.cl',
    password: 'test123',
    note: 'elvir.demo+joven2@gmail.com tiene el inicio de sesión deshabilitado.',
    more: 'Otros jóvenes de prueba: elvir.demo+joven3@gmail.com a elvir.demo+joven6@gmail.com (misma clave).',
  },
};
