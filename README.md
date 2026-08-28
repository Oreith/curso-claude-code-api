# TaskFlow API

Base de la API de TaskFlow: FastAPI gestionada con [uv](https://docs.astral.sh/uv/)
y Python 3.12. En esta entrega solo existe `GET /health`.

## Requisitos

- Python 3.12 (serie 3.12).
- uv.
- Docker con Compose v2.

## Recorrido

```bash
# 1. Instalar dependencias exactamente como están fijadas en uv.lock
uv sync --frozen

# 2. Ejecutar los tests
uv run pytest -q

# 3. Comprobar el estilo con Ruff
uv run ruff check .

# 4. Levantar PostgreSQL en segundo plano
docker compose up -d

# 5. Servir la API en local (http://127.0.0.1:8000)
uv run uvicorn app.main:app --reload

# 6. Al terminar, parar y retirar los contenedores
docker compose down
```

`GET /health` responde `200` con `{"status": "ok"}`.

## Configuración

`compose.yaml` trae valores locales por defecto, así que arranca sin `.env`. Para
personalizarlo, copia `.env.example` a `.env` y ajusta `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `POSTGRES_DB` y `POSTGRES_PORT`.
