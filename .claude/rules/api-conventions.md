# Convenciones de la API

## Dónde viven los endpoints

- `app/routers/projects.py` — CRUD de `/projects` (`APIRouter(prefix="/projects")`).
- `app/routers/tasks.py` — CRUD de `/tasks` (`APIRouter(prefix="/tasks")`).
- `app/routers/__init__.py` — paquete (vacío).
- `app/main.py` — `GET /health` y `GET /states` (sobre `app` directamente), y el
  `app.include_router(...)` de los routers anteriores.
- Esquemas de entrada y de salida: `app/schemas.py`.
- Migraciones de esquema: `alembic/versions/`.

## Esquema de respuesta exacto

Todo endpoint nuevo o modificado devuelve **exactamente** los campos que
`docs/contrato-api.md` §Esquemas de Respuesta declara para ese recurso: ni un
campo de más ni uno de menos.

- El modelo de salida (`*Out` en `app/schemas.py`) lleva `extra="forbid"` y solo
  los campos del contrato.
- Un campo opcional ausente se devuelve como `null`, no se omite.
- Cambiar la forma de una respuesta es cambiar comportamiento observable: se
  edita antes `docs/contrato-api.md`, en un commit separado (`CLAUDE.md`
  §Fuentes de verdad).

## Un campo nuevo son tres capas

Un campo que se añade a un recurso se implementa en las tres, en este orden:

1. **Migración** — `alembic/versions/`: la columna, con `upgrade`/`downgrade`
   probados en ambos sentidos, y la restricción a nivel de base si el valor es
   un conjunto cerrado (`CHECK`, FK).
2. **Esquema** — `app/schemas.py`: el campo en `*Create`, `*Update` y `*Out`.
3. **Validación** — el router en `app/routers/`: rechazo con `422` de los
   valores que el contrato no admite, antes de tocar la base.

El campo `priority` de la tarea (Lab 01) es el ejemplo de referencia: migración
`…_anade_priority_a_tasks.py` con `CHECK ck_tasks_priority`; `priority` en los
tres esquemas `Task*` de `app/schemas.py`; `_valida_priority` en
`app/routers/tasks.py`, llamado desde `POST` y `PATCH`.
