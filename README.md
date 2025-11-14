# Hospital Management API (Django + DRF)

Backend para el sistema de gestión de hospitales/consultas médicas. Expone una API REST construída con **Django 5**, **Django REST Framework** y autenticación **JWT (SimpleJWT)** pensada para ser consumida por un frontend en Next.js.

## Funcionalidades principales

- Usuario personalizado con roles `ADMIN`, `DOCTOR` y `PATIENT`.
- Gestión completa de pacientes, médicos, especialidades, horarios y citas con validación de solapamientos.
- Historias clínicas editables solo por el médico asignado o administradores.
- Confirmación de citas vía email con token y endpoint `/api/email/confirm`.
- Exportaciones en PDF/Excel y métricas para dashboard administrativo.
- Documentación automática con **drf-spectacular** en `/api/docs`.
- Tareas Celery (envío de correo) con soporte para Redis.
- Suite básica de pruebas de integración (auth, permisos, citas, dashboard).

## Requisitos

- Python 3.12+
- (Opcional) PostgreSQL 14+ para entorno productivo.
- Redis si se desea ejecutar Celery fuera de modo eager.

## Configuración local rápida

```powershell
cd "C:\Users\Admin\Desktop\Django\Proyecto final\backend"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Variables de entorno relevantes (añadir a `.env` o al entorno del sistema):

| Variable | Descripción | Default |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Clave secreta | `dev-secret-key-change-me` |
| `DJANGO_DEBUG` | `true/false` | `true` |
| `POSTGRES_*` | Configuración PostgreSQL (`DB`, `USER`, `PASSWORD`, `HOST`, `PORT`) | Si no se define usa SQLite |
| `FRONTEND_URL` | URL base del frontend para enlaces de confirmación | `http://localhost:3000` |
| `EMAIL_BACKEND` | Backend de correo de Django | Consola |
| `CELERY_BROKER_URL` | Broker (Redis recomendado) | `redis://localhost:6379/0` |
| `CELERY_TASK_ALWAYS_EAGER` | Ejecutar tareas de Celery en el mismo proceso (útil en dev) | `1` |

Ejecutar migraciones y servidor:

```powershell
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py runserver
```

### Datos de ejemplo

Para poblar la base de datos local con la informaci��n del archivo `fixtures/sample_data.json`:

```powershell
.venv\Scripts\python manage.py load_sample_data
```

Si necesitas reinstalar los datos (por ejemplo, para reiniciar el estado), puedes usar la opci��n `--force`, que limpia las tablas antes de volver a cargar el fixture:

```powershell
.venv\Scripts\python manage.py load_sample_data --force
```

## Endpoints clave

Todos los endpoints se exponen bajo `/api/`.

- **Auth**: `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`, `POST /auth/register` (opcional).
- **Usuarios**: `GET/POST /users`, `POST /users/{id}/activate`, `POST /users/{id}/deactivate` (solo ADMIN).
- **Pacientes**: `GET/POST /patients`, `GET /patients/search?q=...`.
- **Médicos**: `GET/POST /doctors`, `GET /doctors/{id}/schedule`, `GET /doctors/by-specialty/{id}`.
- **Especialidades**: `GET/POST /specialties`.
- **Horarios**: `GET/POST /schedules`.
- **Citas**: `GET/POST /appointments`, `POST /appointments/{id}/confirm`, `POST /appointments/{id}/cancel`, `GET /appointments/availability?doctor_id=&date=YYYY-MM-DD`.
- **Historias clínicas**: `GET/POST /records`, `GET /records/patient/{id}`, `GET /records/appointment/{id}`.
- **Exportaciones**: `/export/appointments.pdf`, `/export/appointments.xlsx`, `/export/patients.xlsx`.
- **Dashboard**: `GET /dashboard/metrics?from=&to=`.
- **Confirmación email**: `GET /email/confirm?token=...`.

Permisos:

- `ADMIN`: acceso total.
- `DOCTOR`: registros propios (pacientes atendidos, citas, historias, horarios propios).
- `PATIENT`: información propia (citas, historias, perfil).

## Celery y correo

Las tareas de correo se enrutan vía Celery (`hospital.tasks.send_confirmation_email_task`). En desarrollo se ejecutan en el mismo proceso (`CELERY_TASK_ALWAYS_EAGER=1`). Para usar Redis real:

```powershell
set CELERY_TASK_ALWAYS_EAGER=0
celery -A config worker -l info
```

## Tests automatizados

```powershell
.venv\Scripts\python manage.py test
```

Cubre:

- Login + visibilidad de recursos por rol.
- Creación de citas y validación de solapes.
- Confirmación de cita mediante token.
- Métricas del dashboard.

## Documentación OpenAPI

- Esquema JSON: `/api/schema/`
- UI Swagger: `/api/docs/`

Con `drf-spectacular`, cualquier cambio en ViewSets/Serializers se refleja automáticamente.
