# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este repo

API de TaskFlow para un curso, construida con FastAPI, gestionada con `uv` y
Python 3.12 (serie fija `>=3.12,<3.13`). El curso avanza por entregas
incrementales ("sesión 7", "sesión 10", …). Estado actual: solo `GET /health`
implementado (`app/main.py`).

## Comandos

```bash
uv sync --frozen                              # instalar deps exactas de uv.lock
uv run pytest -q                              # todos los tests
uv run pytest -q tests/test_health.py         # un archivo
uv run pytest -q tests/test_health.py::test_health_body   # un test
uv run ruff check .                           # lint (no hay config de autofix; usar --fix a mano)
docker compose up -d                          # PostgreSQL 18 en background
uv run uvicorn app.main:app --reload          # servir en http://127.0.0.1:8000
docker compose down                           # parar contenedores (conserva el volumen postgres_data)
```

Ruff aplica reglas `E, F, I, UP, B` con `line-length = 88`. `pytest` está fijado
a `testpaths = ["tests"]`.

`compose.yaml` trae defaults locales, así que el stack arranca sin `.env`. Para
personalizar, copia `.env.example` a `.env`.

## Arquitectura y fuentes de verdad

Este repo tiene **dos documentos normativos** que mandan sobre el código:

- **`docs/contrato-api.md`** — fuente de verdad del **comportamiento observable**.
  Se autodeclara vinculante: los códigos de estado, esquemas de respuesta y
  ordenamientos de sus tablas son parte del contrato y la sesión 10 los compara
  al revisar. Ante conflicto entre código/tests y el contrato, **gana el
  contrato**; los tests pueden añadir casos pero no debilitar sus invariantes.
  No cambies un código o esquema sin editar antes este documento.
- **`README.md`** — fuente de verdad **operativa** (requisitos y comandos).
- **`docs/onboarding.md`** — briefing con separación explícita de Hechos /
  Inferencias / Desconocidos, y una lista de decisiones aún sin tomar (sección 5).
  Consúltalo antes de asumir cómo está resuelta la persistencia.

Invariantes del contrato que son fáciles de romper al implementar:

- **Esquemas exactos, "ni más ni menos".** Un campo de sobra rompe igual que uno
  que falta. Campo opcional ausente → se serializa como `null`, no se omite.
- **Errores con forma `{"detail": "<mensaje>"}`.** La clave raíz siempre es
  `detail`. Para `422` de validación se admite además la forma que genere el
  framework (con FastAPI, la lista bajo `detail`).
- **`due_at`** se serializa siempre en UTC con sufijo `Z` (no `+00:00`) y sin
  microsegundos: `2026-03-01T09:00:00Z`. Fecha sin zona al crear → `422`.
- **Normalización de `title`** (tarea): trim de extremos y rechazo con `422` si no
  queda ningún carácter visible. No basta `strip()`: hay que rechazar por
  categoría Unicode `Cc, Cf, Zl, Zp, Zs` (p. ej. `U+200B` atraviesa `strip()`).
- **Orden determinista** en toda colección: `GET /states` por campo de orden con
  `id` de desempate; `GET /projects` y `GET /tasks` por `id` ascendente.
- **Colecciones** devuelven una lista JSON en la raíz, sin objeto envolvente.
- Referencia a proyecto/estado inexistente **no se crea implícitamente**.
- `DELETE /projects/{id}` con tareas → `409` (sin borrado en cascada).

## Persistencia (aún no implementada)

- Motor: **PostgreSQL 18** (`compose.yaml`), no SQLite. Los tests de persistencia
  deben correr contra Postgres real porque el contrato exige probar migraciones y
  rollback, e IDs generados por la base.
- El catálogo de estados (`PENDIENTE, EN_CURSO, BLOQUEADA, HECHA`) se siembra
  mediante **migración idempotente** (no vía script de init de Docker: quien ya
  tenga el volumen creado nunca recibiría el seed).
- Sin decidir todavía (ver `docs/onboarding.md` §5): herramienta de migraciones
  (¿Alembic?), ORM/capa de datos, driver (`psycopg` vs `asyncpg`), estrategia de
  aislamiento de tests. Confirma con el usuario antes de elegir.

## Secretos

`.env` está en `.gitignore` y nunca fue commiteado; existe una copia local
idéntica a `.env.example` con valores de desarrollo. `.env.example` es plantilla
pública: solo placeholders / valores locales inocuos. Nunca commitees `.env` ni
pongas credenciales reales en `.env.example` o `compose.yaml`.
