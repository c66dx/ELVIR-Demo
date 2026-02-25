# ELVIR Backend

API REST del backend de la plataforma ELVIR, construida con FastAPI y SQLAlchemy.

## Requisitos

- Python 3.11+
- pip

## Instalación

```bash
cd code/backend
pip install -r requirements.txt
```

## Ejecución

1. Crear base de datos y cargar datos iniciales:

```bash
python seed.py
```

2. Iniciar el servidor:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en `http://localhost:8000`.

- Documentación Swagger: `http://localhost:8000/docs`
- Documentación ReDoc: `http://localhost:8000/redoc`

## Usuarios de prueba (tras ejecutar seed)

| Email | Contraseña | Rol |
|-------|------------|-----|
| joven1@test.cl | test123 | JOVEN |
| joven2@test.cl | test123 | JOVEN |
| prof@test.cl | test123 | PROFESIONAL |
| admin@test.cl | test123 | ADMIN |

## Configuración

Copiar `.env.example` a `.env` y ajustar si es necesario. Variables de entorno (opcional, archivo `.env`):

- `DATABASE_URL`: URL de conexión (default: `sqlite:///./elvir.db`)
- `SECRET_KEY`: Clave para JWT (cambiar en producción)
- `CORS_ORIGINS`: Orígenes permitidos para CORS (default: `http://localhost:4200`)
- `APP_BASE_URL`: URL base para enlaces de activación (default: `http://localhost:4200`)
- `LIVEAVATAR_API_KEY`, `LIVEAVATAR_CONTEXT_ID`, `LIVEAVATAR_AVATAR_ID`, `LIVEAVATAR_VOICE_ID`: Para integración con LiveAvatar (simulación con avatar)

## Conectar el frontend

El frontend usa `ApiService` y se conecta a `http://localhost:8000/api/v1` por defecto. La URL se configura en `code/frontend/src/environments/environment.ts`.
