# Plan — Tareas, v1 y v2 completas (`/tasks`)

Estado: **propuesto, pendiente de aprobación**. Hoy solo se acuerda el plan; no
se edita código, tests, migraciones ni configuración.

## Fuentes

Se planifica contra estas secciones concretas:

- **`docs/contrato-api.md`**
  - §Convenciones (7–18): JSON UTF-8, fechas ISO 8601, IDs enteros positivos
    generados por la base, `404` para inexistente, `409` para conflicto, `422`
    para entrada inválida, errores `{"detail": "<mensaje>"}` (para el `422` de
    validación vale además la forma de FastAPI, con clave raíz `detail`), y
    *"Una referencia a proyecto o estado inexistente no se crea implícitamente"*.
  - §Normalización de texto (20–31): se aplica a `title` de tarea, antes de
    validar y guardar; se recorta el espacio de los extremos y se rechaza con
    `422` el valor que no deja **ningún carácter visible**; la comprobación es
    por categoría Unicode, rechazando `Cc`, `Cf`, `Zl`, `Zp`, `Zs`.
  - §Orden de las listas (33–42): `GET /tasks` por `id` ascendente, *también con
    filtros aplicados*.
  - §Tareas v1 (97–107): campos `id`, `title`, `description` opcional,
    `project_id`, `state_id`; tabla de métodos.
  - §Tareas v2: Fechas Límite (109–119): `due_at` opcional, con zona horaria,
    normalizado a UTC; omitirlo conserva compatibilidad v1; una fecha sin zona
    se rechaza con `422`; `GET /tasks?overdue=true` devuelve tareas con `due_at`
    anterior al instante de evaluación y estado distinto de `HECHA`; una tarea
    sin fecha no está vencida. Fuera de alcance de v2: recordatorios, scheduler,
    zona preferida, cambio automático de estado.
  - §Esquemas de Respuesta (121–150): forma exacta de la tarea
    `{id, title, description, project_id, state_id, due_at}` (en v1, sin
    `due_at`) **ni más ni menos**; opcional ausente como `null`; `due_at`
    siempre en UTC con sufijo `Z`, sin desplazamiento y sin microsegundos;
    colección como lista JSON en la raíz.
  - §Matriz Mínima de Tests (152–167): *CRUD feliz … de tareas*, *IDs
    inexistentes*, *Título vacío y espacios ASCII* (los invisibles Unicode como
    regresión en la sesión 7), *Proyecto o estado inexistente al crear una
    tarea*, *Filtros solos y combinados*, *Orden estable*, *Esquema de respuesta
    exacto*, *Migración desde base vacía y rollback de v2*, *`due_at` omitido,
    válido, sin zona, vencido, futuro y tarea hecha*.
- **`docs/decisiones-ingenieria.md`**: PostgreSQL real (SQLite fuera); esquema
  solo por migraciones de Alembic con `upgrade`/`downgrade` probados en ambos
  sentidos; nada de crear esquema por importación; una capacidad nueva empieza
  por un test que falla.
- **`docs/onboarding.md`** §5: decisiones abiertas. Aplican la nº 8 (forma del
  `422`) y la nº 10 (dónde se normaliza `due_at`); ambas se cierran en este plan
  (ver Decisiones). Las de stack (Alembic, SQLAlchemy 2.x síncrono, `psycopg`
  v3) ya están cerradas y aplicadas.
- **`CLAUDE.md`**: normalización de `title` por categoría Unicode
  `Cc, Cf, Zl, Zp, Zs`; `due_at` en UTC con `Z`, sin microsegundos; migraciones
  probadas en ambos sentidos; no debilitar tests.
- **`README.md`**: comandos de operación y de migraciones.
- **`docs/plan-projects.md`** y el código de `/projects` ya integrado
  (`app/routers/projects.py`, `app/schemas.py`, `tests/test_projects_crud.py`):
  referencia de formato y de patrones a reutilizar.

### Huecos declarados

- `docs/contrato-api.md:79` enlaza `../docs/glosario.md#idempotente`, que no
  existe en el repositorio (ya registrado en `docs/onboarding.md`). No afecta a
  este plan.
- No hay especificación OpenAPI escrita a mano; la que exista la genera FastAPI
  y no se usa como fuente de verdad.

## Alcance

`/tasks` completo, v1 y v2, servido desde el PostgreSQL real de `compose.yaml`:
`POST`, `GET` (colección con filtros `project_id`, `state_id` y `overdue`),
`GET /{id}`, `PATCH /{id}`, `DELETE /{id}`, con normalización completa de
`title` (categoría Unicode), el campo `due_at` (migración con rollback,
validación de zona, serialización en UTC con `Z`) y el filtro
`GET /tasks?overdue=true`.

## Fuera de alcance

Este plan **no** aborda:

- Recordatorios, scheduler, zona horaria preferida del usuario y cambio
  automático de estado (excluidos por §Tareas v2).
- El caso adversario concreto de `title` de la **sesión 7** (*"un título que
  parece válido y no lo es"*): este plan implementa el rechazo por las cinco
  categorías Unicode y lo prueba con caracteres representativos; la sesión 7
  puede añadir encima su caso de regresión.
- Cualquier endpoint o campo de tarea no listado en §Tareas v1 / §Tareas v2
  (asignados, etiquetas, comentarios, orden configurable, paginación).
- Borrado en cascada, unicidad de `title`, autenticación.
- Cambios a `docs/contrato-api.md`, `docs/decisiones-ingenieria.md`,
  `CLAUDE.md`. `README.md` solo se amplía con endpoints y comandos.
- CI, hooks, servicio `api` en `compose.yaml`, y `pyproject.toml` / `uv.lock`
  (todo lo necesario está en la stdlib: `unicodedata`, `datetime`).

## Archivos protegidos

No se abren, muestran ni editan: `.env`. No se modifican:
`docs/contrato-api.md`, `docs/decisiones-ingenieria.md`, `CLAUDE.md`,
`.gitignore`, `pyproject.toml`, `uv.lock`. `.env.example` es la única fuente de
nombres de variables; este plan no necesita ninguna nueva.

## Decisiones (resueltas con evidencia del repositorio)

Ninguna queda en condicional.

### D1 — `title`: normalización completa por categoría Unicode, en este plan

Confirmado con el usuario (2026-09-06). El helper vive en `app/schemas.py`:
recorta con `strip()` y rechaza con `422` si, tras recortar, **ningún** carácter
queda fuera de `{Cc, Cf, Zl, Zp, Zs}` (`unicodedata.category`). Cubre a la vez
el caso "vacío" y el "solo invisibles". Lo que se guarda es el valor recortado;
no se eliminan invisibles interiores (el contrato solo exige que quede al menos
un carácter visible). Evidencia: `docs/contrato-api.md:20–31`, `CLAUDE.md`
§"Al implementar".

### D2 — `project_id` / `state_id` inexistentes en `POST` y `PATCH` → `422`

La referencia a una fila que no existe es **entrada inválida**
(`docs/contrato-api.md:10`, `:18`), y §Tareas v1 dice que `POST /tasks`
*"valida proyecto, estado y título"*. La API comprueba con `session.get(...)`
antes de insertar y responde `422 {"detail": "<campo> no corresponde a ningún
registro"}`. La FK `NOT NULL` + `ON DELETE RESTRICT` de la tabla es la red de
fondo.

### D3 — Id de tarea inexistente en `GET /{id}`, `PATCH /{id}`, `DELETE /{id}` → `404`

`docs/contrato-api.md:10` (*"`404` para recurso inexistente"*) y la Matriz
Mínima (*"IDs inexistentes"*). El contrato solo detalla el camino feliz de
`DELETE` (`204` sin cuerpo); el `404` para id ausente es la convención general,
igual que en `/projects`.

### D4 — Normalización de `due_at`: en los esquemas de `app/schemas.py`

Cierra `docs/onboarding.md` §5 nº 10 (la decisión abierta era *dónde*). Entrada:
un `field_validator` en `TaskCreate` / `TaskUpdate` rechaza el `datetime` naive
(sin zona) con `422` y convierte el aware a UTC. Salida: un `field_serializer`
en `TaskOut` emite `"%Y-%m-%dT%H:%M:%SZ"` (UTC, sufijo `Z`, sin desplazamiento,
sin microsegundos). Se elige la capa de esquemas porque el repo ya ubica ahí
toda validación/normalización (`_name_limpio`, validadores de `Project*`).
Evidencia: `docs/contrato-api.md:112–113`, `:146–148`; `CLAUDE.md`
§"Al implementar".

### D5 — Forma del `422`

Cierra `docs/onboarding.md` §5 nº 8. Se acepta tal cual: para errores propios
(`HTTPException`) el cuerpo es `{"detail": "<mensaje>"}`; para errores de
validación de Pydantic/FastAPI es `{"detail": [ ... ]}`. En ambos la clave raíz
es `detail`, que es lo único que exige `docs/contrato-api.md:14–17`. Los tests
comprueban `"detail" in cuerpo`, no la forma interna.

### D6 — Columna `due_at`: `TIMESTAMP WITH TIME ZONE`, `NULL`

`docs/contrato-api.md:111` (*"con zona horaria y normalizado a UTC"*,
*"opcional"*). `sa.DateTime(timezone=True)`; PostgreSQL guarda el instante en
UTC y devuelve `datetime` aware.

### D7 — `overdue=true` se combina (AND) con `project_id` y `state_id`

`docs/contrato-api.md:41` (*"también con filtros aplicados"*) y §Tareas v1
(filtros *"solos o combinados"*); nada indica exclusividad. `overdue` es
`bool = False`; solo `true` activa el filtro.

### D8 — "Instante de evaluación" de `overdue` = `now()` de la base

`docs/contrato-api.md:115`. El filtro se evalúa en SQL con `func.now()`
(`TIMESTAMP WITH TIME ZONE` de la transacción), no con el reloj del proceso, para
tener una sola fuente de tiempo y evitar desajustes de zona.

### D9 — `PATCH /tasks/{id}` "consistente"

`docs/contrato-api.md:106`. Solo se modifican los campos presentes en el cuerpo
(`model_dump(exclude_unset=True)`). Si viene `title`, se normaliza (D1) y no
puede quedar sin carácter visible (`422`). Si viene `project_id` o `state_id`,
debe existir (`422`, D2). Si viene `due_at`, se valida la zona (D4). `{}` → `200`
sin cambios. `description` y `due_at` admiten `null` explícito.

### D10 — Esquema de respuesta de tarea, exacto

`docs/contrato-api.md:121–142`. `TaskOut` con
`ConfigDict(from_attributes=True, extra="forbid")`. v1: exactamente `id`,
`title`, `description`, `project_id`, `state_id`. v2: además `due_at`. Opcional
ausente como `null`. Colección: `response_model=list[TaskOut]` → lista JSON en
la raíz.

### D11 — Modelo `Task` alineado con el esquema real

`app/models.py` describe tablas existentes. En los Incrementos 2–4 `Task` tiene
5 columnas; el Incremento 5 le añade `due_at` a la vez que la migración.

### D12 — `GET /tasks` con un filtro sin coincidencias → `200` con lista vacía

Un filtro de colección no es un acceso a recurso: `GET /tasks?project_id=9999`
devuelve `200 []`, no `404`. Evidencia: §Tareas v1 (*"admite `project_id` y
`state_id`"*), §Convenciones (`404` es para "recurso inexistente" en la ruta).

### D13 — Tests que evolucionan de v1 a v2

`tests/test_migrations_tasks.py::test_columnas_de_tasks_sin_due_at` y las
aserciones de esquema de tarea de los Incrementos 2–4 afirman el esquema **v1
exacto**. El contrato ya distingue v1 y v2 (*"Tarea (v2; en v1, sin due_at)"*),
así que añadir `due_at` es evolución acordada, no un cambio de contrato. Esas
aserciones se actualizan al esquema v2 exacto **en el mismo incremento que
introduce `due_at`** (Incremento 5 para la migración, Incremento 6 para
`TaskOut`): no pueden actualizarse antes porque la aserción nueva fallaría sin
la columna. Siguen siendo comprobaciones `set(...) ==` exactas; no se debilita
ninguna.

## Patrones que se reutilizan

- **Esquemas**: `app/schemas.py::_name_limpio` y los validadores de `Project*`
  (`field_validator`, `extra="forbid"`, `model_dump(exclude_unset=True)`).
- **Router**: `app/routers/projects.py` — `APIRouter(prefix=...)`, helper
  `_get_or_404`, `session.commit()/refresh()`, `response_model`.
- **Tests de endpoint**: `tests/test_projects_crud.py` — fixtures `engine`
  (scope módulo, `pytest.skip` si la base no responde), `migrada` (`upgrade
  head` → `downgrade base`), `tablas_limpias` autouse con
  `TRUNCATE tasks, projects RESTART IDENTITY CASCADE`, `client` con
  `TestClient`.
- **Tests de migración**: `tests/test_migrations_projects.py` /
  `tests/test_migrations_tasks.py` — introspección con `inspect(engine)`,
  ciclo `upgrade head` ↔ `downgrade base`.
- **Inserción directa en `tasks`** para preparar estado sin endpoint (como en
  `tests/test_projects_delete.py`): ya no hace falta a partir del Incremento 2,
  pero sirve de referencia para `state_id` reales del catálogo sembrado.

## Incrementos

Cada incremento = un commit, confirmado solo con su **Comprobación**. Una
capacidad nueva empieza por un test que falla por su ausencia. No se debilita
ningún test para conseguir verde.

Todos los comandos `alembic` y `pytest` de persistencia asumen la base de
Compose levantada y las `POSTGRES_*` de `compose.yaml` en el entorno:

```bash
docker compose up -d && docker compose ps        # 'db' healthy
export POSTGRES_USER=taskflow POSTGRES_PASSWORD=taskflow_local \
       POSTGRES_DB=taskflow POSTGRES_HOST=localhost POSTGRES_PORT=5432
```

### Incremento 1 — Normalización de `title` (helper + tests unitarios)

**Objetivo:** un helper en `app/schemas.py` que recorta `title` y rechaza con
error de validación el valor sin ningún carácter visible, por categoría Unicode.

**Toca:** `app/schemas.py` (helper `_titulo_normalizado`, `import unicodedata`),
`tests/test_title_normalizacion.py` *(nuevo, sin base de datos)*.

**Test que falla primero:** `tests/test_title_normalizacion.py` —

- `"  Regar  "` → `"Regar"`;
- `""`, `"   "` (Zs ASCII), `"  "` (Zs), `"​"` (Cf, ZERO WIDTH
  SPACE), `"\x00"` (Cc), `" "` (Zl), `" "` (Zp) → `ValueError`;
- `"Regar​las plantas"` y `"​Regar"` → se aceptan (tienen visibles) y
  se devuelven recortados, con los invisibles interiores intactos.

Falla hoy porque el helper no existe.

**Comprobación:**
```bash
uv run pytest -q tests/test_title_normalizacion.py
uv run ruff check .
```
Éxito: todos los casos verdes; el helper no toca base de datos.

### Incremento 2 — Modelo `Task`, `POST /tasks` y `GET /tasks/{id}`

**Objetivo:** crear una tarea (`201`, validando proyecto, estado y título) y
leerla por id (`200` / `404`), con el esquema v1 exacto.

**Toca:** `app/models.py` (`class Task`, 5 columnas), `app/schemas.py`
(`TaskCreate` con `extra="forbid"` y `title` normalizado vía Incremento 1;
`TaskOut` v1), `app/routers/__init__.py` ya existe, `app/routers/tasks.py`
*(nuevo, `APIRouter(prefix="/tasks", tags=["tasks"])`)*, `app/main.py`
(`app.include_router(tasks.router)`), `tests/test_tasks_crud.py` *(nuevo)*.

**Test que falla primero:** `tests/test_tasks_crud.py` —

- `test_post_crea_201_y_esquema_v1_exacto`: `set(body) == {"id","title",
  "description","project_id","state_id"}`, `description` a `null`;
- `test_post_title_vacio_o_espacios_422`, `test_post_title_invisible_422`
  (`U+200B`);
- `test_post_project_id_inexistente_422`, `test_post_state_id_inexistente_422`
  (clave raíz `detail`);
- `test_post_campo_desconocido_422`;
- `test_get_por_id_200_esquema_v1_exacto`, `test_get_por_id_inexistente_404`,
  `test_get_por_id_no_entero_422`.

**Comprobación:**
```bash
uv run alembic upgrade head
uv run pytest -q tests/test_tasks_crud.py
uv run ruff check .
# manual (uv run uvicorn app.main:app):
curl -s -i -X POST localhost:8000/tasks -H 'content-type: application/json' \
  -d '{"title":"Regar","project_id":1,"state_id":1}'      # 201, 5 claves
curl -s -X POST localhost:8000/tasks -H 'content-type: application/json' \
  -d '{"title":"x","project_id":9999,"state_id":1}'        # 422 {"detail": ...}
```
Éxito: `201` con 5 claves exactas; `422` con clave raíz `detail` para título
inválido y para referencias inexistentes; `GET /{id}` `200`/`404`.

### Incremento 3 — `GET /tasks` con filtros `project_id` y `state_id`

**Objetivo:** listar tareas (`200`, lista JSON en la raíz, orden por `id`
ascendente), con `project_id` y `state_id` opcionales, solos o combinados.

**Toca:** `app/routers/tasks.py` (`GET ""` con query params opcionales),
`tests/test_tasks_list.py` *(nuevo)*.

**Test que falla primero:** `tests/test_tasks_list.py` —

- `test_lista_vacia_es_lista`: `[]`;
- `test_orden_por_id_estable`: crea varias, ids ascendentes, dos llamadas
  idénticas devuelven lo mismo;
- `test_filtro_project_id`, `test_filtro_state_id`, `test_filtros_combinados`;
- `test_filtro_sin_coincidencias_200_lista_vacia` (`project_id=9999` → `200 []`).

**Comprobación:**
```bash
uv run pytest -q tests/test_tasks_list.py
uv run ruff check .
curl -s 'localhost:8000/tasks?project_id=1&state_id=2'      # 200, lista filtrada
```
Éxito: lista JSON en la raíz, orden por `id` estable, filtros solos y
combinados, filtro sin coincidencias → `200 []`.

### Incremento 4 — `PATCH /tasks/{id}` y `DELETE /tasks/{id}`

**Objetivo:** actualización parcial consistente (`200` / `404` / `422`) y
borrado (`204` sin cuerpo / `404`).

**Toca:** `app/schemas.py` (`TaskUpdate`: todos los campos opcionales,
`extra="forbid"`, `title` normalizado si viene), `app/routers/tasks.py`
(`PATCH "/{task_id}"`, `DELETE "/{task_id}"`), `tests/test_tasks_crud.py`
(añadir casos).

**Test que falla primero:**

- `test_patch_cambia_solo_lo_enviado`, `test_patch_cuerpo_vacio_200_sin_cambios`,
  `test_patch_description_a_null`;
- `test_patch_title_invisible_422`, `test_patch_project_id_inexistente_422`,
  `test_patch_state_id_inexistente_422`, `test_patch_id_inexistente_404`,
  `test_patch_campo_desconocido_422`;
- `test_delete_204_sin_cuerpo` (`resp.content == b""`),
  `test_delete_id_inexistente_404`;
- `test_delete_ultima_tarea_permite_borrar_el_proyecto`: tras borrar la única
  tarea de un proyecto, `DELETE /projects/{id}` pasa de `409` a `204`
  (integración con §Proyectos).

**Comprobación:**
```bash
uv run pytest -q tests/test_tasks_crud.py
uv run ruff check .
curl -s -X PATCH localhost:8000/tasks/1 -H 'content-type: application/json' \
  -d '{"state_id":3}'                                        # 200, resto intacto
curl -s -i -X DELETE localhost:8000/tasks/1                  # 204 sin cuerpo
```
Éxito: `PATCH` solo toca lo enviado y valida referencias/título; `{}` → `200`
sin cambios; `DELETE` → `204` sin cuerpo; `404` para id inexistente en ambos.

### Incremento 5 — Migración de `due_at` (columna + rollback) y modelo

**Objetivo:** añadir `tasks.due_at` (`TIMESTAMP WITH TIME ZONE`, `NULL`) por una
revisión de Alembic con `downgrade` que la elimina, y reflejarla en el modelo.

**Toca:** `alembic/versions/<rev>_anade_due_at_a_tasks.py` *(nueva;
`down_revision = "08b6d37b717e"`)*, `app/models.py` (`Task.due_at`),
`tests/test_migrations_due_at.py` *(nuevo)*, `tests/test_migrations_tasks.py`
(actualizar `test_columnas_de_tasks_sin_due_at` → esquema v2 exacto, D13).

**Test que falla primero:** `tests/test_migrations_due_at.py` —

- tras `upgrade head`, `tasks` tiene `due_at`, `nullable is True`, tipo con
  zona (`str(type)` contiene `TIMESTAMP` y la reflexión marca `timezone`);
- `downgrade -1` elimina solo `due_at` y conserva las otras columnas y las FKs;
- `upgrade head` la reañade.

**Comprobación:**
```bash
uv run alembic upgrade head
uv run alembic downgrade -1        # revierte solo due_at  -> rollback de v2
uv run alembic upgrade head
uv run pytest -q tests/test_migrations_due_at.py tests/test_migrations_tasks.py \
                 tests/test_migrations_cycle.py
uv run ruff check .
```
Éxito: la columna aparece y desaparece con la revisión; el ciclo `head` ↔
`base` sin error; `test_migrations_tasks.py` verde con la aserción v2.

### Incremento 6 — `due_at` en entrada y salida (`POST`, `PATCH`, `TaskOut`)

**Objetivo:** aceptar `due_at` opcional (rechazando el que no lleva zona,
normalizando a UTC) y devolverlo siempre en UTC con sufijo `Z` y sin
microsegundos; omitirlo conserva el comportamiento v1.

**Toca:** `app/schemas.py` (`due_at` en `TaskCreate`, `TaskUpdate`, `TaskOut`;
`field_validator` de zona → UTC; `field_serializer` de salida),
`app/routers/tasks.py` (pasar `due_at` en crear/actualizar),
`tests/test_tasks_due_at.py` *(nuevo)*, y actualizar a esquema v2 exacto las
aserciones de `set(body) == {...}` de `tests/test_tasks_crud.py` y
`tests/test_tasks_list.py` (D13).

**Test que falla primero:** `tests/test_tasks_due_at.py` —

- `test_post_sin_due_at_devuelve_null` (compat v1);
- `test_post_due_at_con_offset_se_devuelve_en_z_sin_micros`: entrada
  `"2026-03-01T11:00:00+02:00"` → salida `"2026-03-01T09:00:00Z"`;
- `test_post_due_at_sin_zona_422` (`"2026-03-01T09:00:00"`);
- `test_post_due_at_con_microsegundos_se_trunca`;
- `test_patch_due_at_pone_y_quita` (`null` explícito);
- `test_esquema_v2_exacto`: `set(body) == {"id","title","description",
  "project_id","state_id","due_at"}`.

**Comprobación:**
```bash
uv run pytest -q tests/test_tasks_due_at.py tests/test_tasks_crud.py \
                 tests/test_tasks_list.py
uv run ruff check .
curl -s -X POST localhost:8000/tasks -H 'content-type: application/json' \
  -d '{"title":"x","project_id":1,"state_id":1,"due_at":"2026-03-01T11:00:00+02:00"}'
#   201  "due_at":"2026-03-01T09:00:00Z"
curl -s -X POST localhost:8000/tasks -H 'content-type: application/json' \
  -d '{"title":"x","project_id":1,"state_id":1,"due_at":"2026-03-01T09:00:00"}'
#   422  {"detail": ...}
```
Éxito: `due_at` omitido → `null`; con offset → UTC con `Z` sin microsegundos;
sin zona → `422`; esquema de salida v2 exacto (un solo campo más que v1).

### Incremento 7 — `GET /tasks?overdue=true`

**Objetivo:** filtrar las tareas con `due_at` anterior a `now()` y estado
distinto de `HECHA`; una tarea sin `due_at` nunca aparece; combinable con
`project_id` y `state_id`; orden por `id`.

**Toca:** `app/routers/tasks.py` (`overdue: bool = False`; cuando `true`,
`WHERE due_at IS NOT NULL AND due_at < now() AND state_id <> (SELECT id FROM
states WHERE code = 'HECHA')`), `tests/test_tasks_overdue.py` *(nuevo)*.

**Test que falla primero:** `tests/test_tasks_overdue.py` —

- `test_vencida_aparece` (due_at en el pasado, estado `PENDIENTE`);
- `test_futura_no_aparece`;
- `test_sin_due_at_no_aparece`;
- `test_vencida_pero_hecha_no_aparece`;
- `test_overdue_combinado_con_project_id`;
- `test_overdue_orden_por_id_estable`.

**Comprobación:**
```bash
uv run pytest -q tests/test_tasks_overdue.py
uv run pytest -q                     # SUITE COMPLETA en verde
uv run ruff check .
curl -s 'localhost:8000/tasks?overdue=true'
curl -s 'localhost:8000/tasks?overdue=true&project_id=1'
```
Éxito: solo las vencidas y no `HECHA` con `due_at`; combinación con otros
filtros correcta; orden estable; suite completa verde.

### Incremento 8 — README y repaso de la Matriz Mínima

**Objetivo:** dejar `README.md` al día y verificar que la suite cubre las filas
de la Matriz Mínima relativas a tareas y a `due_at`.

**Toca:** `README.md` (tabla de endpoints con `/tasks` y sus filtros; nota de
`due_at`/`overdue`). Solo si el repaso detecta un hueco real de cobertura: test
adicional en el archivo correspondiente. No se toca contrato.

**Comprobación:**
```bash
uv run pytest -q            # todo verde
uv run ruff check .         # limpio
```
Repaso explícito contra `docs/contrato-api.md:152–167`:

- *CRUD feliz de tareas* → Incrementos 2–4.
- *IDs inexistentes* → `404` en `GET/{id}`, `PATCH/{id}`, `DELETE/{id}`.
- *Título vacío y espacios ASCII* → Incrementos 1–2 (y, de más, los invisibles
  Unicode).
- *Proyecto o estado inexistente al crear una tarea* → Incremento 2 (`422`).
- *Filtros solos y combinados* → Incremento 3 (y `overdue` en el 7).
- *Orden estable* → Incrementos 3 y 7.
- *Esquema de respuesta exacto* → Incrementos 2–4 (v1) y 6 (v2).
- *Migración desde base vacía y rollback de v2* → Incremento 5 y
  `tests/test_migrations_cycle.py`.
- *`due_at` omitido, válido, sin zona, vencido, futuro y tarea hecha* →
  Incrementos 6 y 7.

## Reglas de ejecución

- **Un incremento = un commit**, confirmado **solo** con su sección
  *Comprobación*. El mensaje de commit se muestra antes de crearlo.
- Al terminar un incremento, **parar y esperar aprobación**. No encadenar el
  siguiente.
- Una capacidad nueva **empieza por un test que falla** por su ausencia.
- **No se debilita ni se elimina** un test para conseguir verde. Las
  aserciones de esquema v1 que evolucionan a v2 (D13) se actualizan en el mismo
  incremento que introduce `due_at`, siguen siendo exactas, y el contrato ya
  distinguía ambos esquemas.
- Cada migración implementa `upgrade` y `downgrade` y se prueba **en ambos
  sentidos** antes de integrarse. El esquema no se crea por importación de
  módulos.
- No se abre, muestra ni edita `.env`. `.env.example` es la única fuente de
  nombres de variables. No se toca `pyproject.toml` ni `uv.lock`.
- Los tests de persistencia corren contra el PostgreSQL real de `compose.yaml`;
  si la base no está disponible se marcan `skipped`, no se adaptan a SQLite.
