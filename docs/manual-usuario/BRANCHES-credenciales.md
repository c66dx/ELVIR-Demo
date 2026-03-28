# Credenciales demo: `main` vs otra rama (p. ej. preview)

- **`main`:** `seed.py` crea solo **joven1@test.cl** (login OK) y **joven2@test.cl** (login deshabilitado), más `prof@test.cl` y `admin@test.cl`. Los `environment.ts` / `environment.prod.ts` muestran esos mismos correos.

- **Otra rama** (p. ej. preview / Teletón con Gmail y más jóvenes): debe traer **su propio** `seed.py` y **sus propios** `environment*.ts`. No mezclar: si cambias de rama, borra la base local (`elvir_demo.db` o volumen) y vuelve a `alembic upgrade` + `seed.py`.

- **Render:** debe desplegar la rama que quieras (preview = credenciales extendidas; main = mínimo). El build usa el `environment.prod.ts` **de esa rama**.
