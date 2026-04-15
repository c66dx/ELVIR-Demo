# Deploy backend ELVIR en Northflank Sandbox

Este flujo mueve solo el backend FastAPI a Northflank. El frontend Angular sigue en Vercel y la base de datos sigue en Supabase.

## Cuando conviene

Usa esta opcion si necesitas:

- evitar el sleep de Render Free;
- no usar tarjeta de credito;
- mantener el backend actual casi sin cambios.

Northflank Sandbox es adecuado para demo o piloto. No lo trataria como produccion definitiva.

## Lo que ya tiene el repo

El backend ya esta preparado para este tipo de despliegue:

- `code/backend/Dockerfile`
- `GET /health/live`
- migraciones automaticas en `docker-entrypoint.sh`

No hace falta crear un Dockerfile nuevo.

## Requisitos

Ten a mano estos valores:

- `DATABASE_URL` de Supabase
- `SECRET_KEY` nueva para produccion
- `LIVEAVATAR_API_KEY`
- `LIVEAVATAR_AVATAR_ID`
- `LIVEAVATAR_VOICE_ID`
- URL publica del frontend en Vercel

Genera la `SECRET_KEY` asi:

```bash
openssl rand -hex 32
```

## Paso 1: crear el servicio en Northflank

1. Crea un proyecto nuevo.
2. Crea un servicio desde tu repositorio de GitHub.
3. Selecciona la rama que quieres desplegar.
4. Configura el build con estos valores:

- Build type: `Dockerfile`
- Dockerfile path: `code/backend/Dockerfile`
- Build context: `code/backend`

## Paso 2: exponer el puerto correcto

Configura el servicio HTTP para usar:

- Port: `8000`
- Health path: `/health/live`

## Paso 3: cargar variables de entorno

Toma como base `code/backend/.env.northflank.example`.

Variables minimas para ELVIR:

```env
ENV=prod
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require
SECRET_KEY=<openssl rand -hex 32>
APP_BASE_URL=https://elvir-demo.vercel.app
CORS_ORIGINS=https://elvir-demo.vercel.app
PASSWORD_MIN_LENGTH=12
RATE_LIMIT_TRUST_X_FORWARDED_FOR=true
LIVEAVATAR_API_KEY=...
LIVEAVATAR_API_BASE=https://api.liveavatar.com/v1
LIVEAVATAR_AVATAR_ID=...
LIVEAVATAR_VOICE_ID=...
LIVEAVATAR_CONTEXT_ID=
```

Notas:

- Deja `LIVEAVATAR_CONTEXT_ID` vacio si la app resuelve `liveavatar_context_id` desde `simulation_templates` en la base de datos.
- `RATE_LIMIT_TRUST_X_FORWARDED_FOR=true` es correcto detras del proxy de Northflank.
- `APP_BASE_URL` y `CORS_ORIGINS` deben apuntar al frontend real en Vercel.

## Paso 4: almacenamiento de archivos

Si despliegas con `STORAGE_BACKEND=local`, los uploads viven dentro del contenedor. Eso sirve para probar rapido, pero no es una estrategia fuerte si el servicio se redeploya o se recrea.

Para ELVIR hay dos caminos:

1. `STORAGE_BACKEND=local`
   - util para probar rapido;
   - riesgo: fotos, audios y CV pueden perderse en redeploy.

2. `STORAGE_BACKEND=s3`
   - recomendado si quieres persistencia real;
   - puedes usar S3 compatible, R2, MinIO, etc.

Si quieres una demo seria, sube tambien el storage a S3-compatible.

## Paso 5: desplegar

Haz deploy desde la UI de Northflank.

Cuando termine, valida:

- `https://<tu-servicio>.northflank.app/health/live`
- `https://<tu-servicio>.northflank.app/health/ready`
- `https://<tu-servicio>.northflank.app/docs`

`/health/live` debe responder 200 siempre.

`/health/ready` debe responder 200 solo si la conexion a Supabase esta correcta.

## Paso 6: apuntar el frontend al nuevo backend

Hoy el frontend de produccion tiene el backend hardcodeado en:

- `code/frontend/src/environments/environment.prod.ts`

Debes cambiar:

```ts
apiUrl: 'https://elvir-demo.onrender.com/api/v1'
```

por algo como:

```ts
apiUrl: 'https://<tu-servicio>.northflank.app/api/v1'
```

Luego redeploy del frontend en Vercel.

## Paso 7: validacion funcional

Despues del cambio, prueba esto:

1. login en Vercel;
2. `GET /health/live`;
3. crear una sesion;
4. abrir LiveAvatar;
5. revisar que `/uploads/...` siga resolviendo si usas fotos o audios.

## Riesgos conocidos

- Sandbox no debe considerarse produccion final.
- Si dejas `STORAGE_BACKEND=local`, los archivos no tienen garantia fuerte de persistencia.
- El frontend seguira apuntando a Render hasta que cambies `environment.prod.ts` y redeployes Vercel.

## Referencias

- Northflank pricing
- Northflank services
- Northflank ports
- Northflank domains
