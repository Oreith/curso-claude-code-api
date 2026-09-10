# TaskFlow API

API de gestión de tareas y proyectos. FastAPI y PostgreSQL, gestionada con
[uv](https://docs.astral.sh/uv/) y Python 3.12.

- **Qué expone la API:** `docs/contrato-api.md` (comportamiento observable
  vinculante: rutas, códigos de estado y esquemas de respuesta).
- **Peticiones listas para ejecutar:** `api.http`, en la raíz del repositorio.

## Requisitos

- Python 3.12 (serie 3.12).
- uv.
- Docker con Compose v2.

## Puesta en marcha

Cada línea es un paso; ejecútalos en este orden desde la raíz del repositorio.

```bash
uv sync --frozen
export POSTGRES_USER=taskflow POSTGRES_PASSWORD=taskflow_local POSTGRES_DB=taskflow POSTGRES_HOST=localhost POSTGRES_PORT=5432
docker compose up -d
docker compose ps
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

- `export ...` publica las variables `POSTGRES_*` en la shell actual. `alembic`
  y `uvicorn` construyen la URL de conexión desde ellas (`app/config.py`) y no
  arrancan si faltan; `docker compose` usa los mismos valores como defaults.
  Para personalizarlos, copia `.env.example` a `.env`, edítalo, y en lugar del
  `export` de arriba usa `set -a && source .env && set +a`.
- `docker compose ps` es una comprobación: espera a que el servicio `db`
  aparezca como `healthy` antes de migrar.
- `uv run uvicorn ...` queda en primer plano sirviendo en
  `http://127.0.0.1:8000`. Se detiene con `Ctrl-C`.

## Probar un endpoint

Con la API en marcha, en otra terminal:

```bash
curl -s http://127.0.0.1:8000/health
```

Responde `200` con `{"status": "ok"}`.

Para el recorrido completo —crear un proyecto, sus tareas, filtrar, y los casos
de error— abre `api.http` con la extensión REST Client de VS Code o el cliente
HTTP de JetBrains y lanza las peticiones de arriba abajo: cada una se apoya en
el resultado de la anterior.

## Tests

Los tests de persistencia corren contra el PostgreSQL real de `compose.yaml`,
no contra SQLite. Con la base levantada (`docker compose up -d`) y `healthy`:

```bash
uv run pytest -q
```

`tests/conftest.py` toma las variables `POSTGRES_*` del entorno; si no están,
carga un `.env` de la raíz (si existe) y, en último caso, usa los valores por
defecto de `compose.yaml`. Si la base no está disponible, los tests de
persistencia se marcan como `skipped` en lugar de fallar.

## Estilo

```bash
uv run ruff check .
```

Ruff aplica `E, F, I, UP, B` con `line-length = 88`, sin autofix configurado.

## Migraciones

El esquema de la base se gestiona solo con Alembic; la URL de conexión la
construye `alembic/env.py` desde las variables `POSTGRES_*` del entorno, no
desde `alembic.ini`.

```bash
uv run alembic upgrade head     # aplica todas las migraciones
uv run alembic downgrade base   # revierte todas las revisiones
uv run alembic downgrade -1     # revierte solo la última
```

## Al terminar

```bash
docker compose down       # para y retira los contenedores; conserva el volumen
```
