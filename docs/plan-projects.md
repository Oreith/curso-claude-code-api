# Plan — CRUD de Proyectos (`/projects`)

Estado: **propuesto, pendiente de aprobación**. Hoy solo se acuerda el plan; no
se edita código, tests, migraciones ni configuración.

## Fuentes

Se planifica contra estas secciones concretas:

- **`docs/contrato-api.md`**
  - §Convenciones (líneas 7–18): JSON UTF-8, fechas ISO 8601, IDs enteros
    positivos **generados por la base**, `404` para inexistente, `409` para
    conflicto, `422` para entrada inválida, errores con forma
    `{"detail": "<mensaje>"}`, y *"Una referencia a proyecto o estado inexistente
    no se crea implícitamente"*.
  - §Orden de las listas (33–42): `GET /projects` ordena por `id` ascendente.
  - §Proyectos (82–96): campos mínimos `id`, `name`, `description` opcional; tabla
    de métodos; `DELETE` devuelve `204` si el proyecto no tiene tareas y `409` si
    las tiene; *"no hay borrado en cascada implícito"*.
  - §Tareas v1 (97–107): columnas de la tabla `tasks` (`id`, `title`,
    `description` opcional, `project_id`, `state_id`) — necesarias para la tabla
    que crea este plan.
  - §Esquemas de Respuesta (121–150): forma exacta del proyecto
    `{"id": 1, "name": "Casa", "description": null}` **ni más ni menos**; un campo
    opcional ausente se devuelve como `null`, no se omite; `GET` de colección
    devuelve una lista JSON en la raíz, sin objeto envolvente.
  - §Matriz Mínima de Tests (152–167): *CRUD feliz de proyectos*, *IDs
    inexistentes*, *Borrado de proyecto con tareas (`409`)*, *Orden estable*,
    *Esquema de respuesta exacto*.
- **`docs/decisiones-ingenieria.md`**: tests de persistencia contra PostgreSQL
  real (SQLite fuera); esquema solo por migraciones de Alembic con
  `upgrade`/`downgrade` probados en ambos sentidos; nada de crear esquema por
  importación de módulos; una capacidad nueva empieza por un test que falla.
- **`docs/onboarding.md`** §5: decisiones abiertas. Las de stack (nºs 1–4:
  Alembic, SQLAlchemy 2.x síncrono, driver `psycopg` v3, aislamiento de tests)
  ya están cerradas en `docs/plan-persistencia.md` §Incremento 0 y aplicadas en
  el código (`app/config.py`, `app/db.py`, `alembic/`). Este plan no reabre
  ninguna y no introduce decisiones nuevas del tipo de §5.
- **`CLAUDE.md`**: límites de trabajo, comandos canónicos, y el matiz de que la
  normalización por categoría Unicode (`Cc, Cf, Zl, Zp, Zs`) es de `title` **de
  tarea**, no de `name` de proyecto.
- **`README.md`**: comandos de operación y de migraciones (`uv run alembic
  upgrade head` / `downgrade`).
- **`docs/plan-persistencia.md`**: referencia de formato y de alcance ya
  cubierto (catálogo de estados y `GET /states`, hasta su Incremento 4).

### Huecos declarados

- `docs/contrato-api.md:79` enlaza `../docs/glosario.md#idempotente`, que **no
  existe** en el repositorio (ya registrado en `docs/onboarding.md` §1 y §5.5).
  No afecta a este plan.
- No hay especificación OpenAPI escrita a mano; la que exista será la que genere
  FastAPI. No se usa como fuente de verdad.

## Alcance

CRUD completo de `/projects` (`POST`, `GET` colección, `GET /{id}`, `PATCH`,
`DELETE`) servido desde el PostgreSQL real de `compose.yaml`, con el esquema de
respuesta exacto del contrato y el orden por `id`. Incluye la migración de la
tabla `projects` y la migración de la tabla `tasks` **solo a nivel de esquema**
(sin endpoints, sin seed), porque el `409` de `DELETE /projects/{id}` es parte
del contrato de Proyectos y no puede cumplirse sin detectar tareas que
referencian el proyecto.

## Fuera de alcance

Este plan **no** aborda:

- Endpoints de tareas (`POST/GET/PATCH/DELETE /tasks`, `GET /tasks/{id}`) —
  corresponden a la sesión *Tareas v1*.
- El campo `due_at`, su normalización a UTC y `GET /tasks?overdue=true` —
  sesión *Tareas v2*; se añadirán por migración con rollback.
- Los filtros de `/tasks` (`project_id`, `state_id`, solos o combinados).
- La normalización por categoría Unicode (`Cc, Cf, Zl, Zp, Zs`) del texto: el
  contrato la acota a `title` **de tarea** (`docs/contrato-api.md:20–31`), y se
  trabaja a fondo en la sesión 7. Este plan no la implementa para `name` de
  proyecto.
- Borrado en cascada de tareas al borrar un proyecto (el contrato lo prohíbe
  explícitamente).
- Unicidad de `name`, autenticación, paginación y cualquier objeto envolvente
  con metadatos en las colecciones.
- CI, hooks y un servicio `api` en `compose.yaml`.
- Modificar los documentos rectores (`docs/contrato-api.md`,
  `docs/decisiones-ingenieria.md`, `CLAUDE.md`). `README.md` solo se amplía con
  información operativa (endpoints y comandos), nunca con contrato.

## Archivos protegidos

No se abren, muestran, editan ni confirman: `.env`. No se modifican:
`docs/contrato-api.md`, `docs/decisiones-ingenieria.md`, `CLAUDE.md`,
`.gitignore`. `.env.example` es la única fuente permitida para nombres de
variables; ya contiene `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`,
`POSTGRES_HOST`, `POSTGRES_PORT` — este plan no necesita variables nuevas.

## Decisiones (resueltas con evidencia del repositorio)

Ninguna queda en condicional. Cada decisión que el plan necesita se cierra aquí
con su evidencia.

### D1 — La tabla `tasks` (solo esquema) se crea en este plan

`DELETE /projects/{id}` debe devolver `409` *"si las tiene"*
(`docs/contrato-api.md:92`) y la Matriz Mínima exige el caso *"Borrado de
proyecto con tareas (`409`)"* (`docs/contrato-api.md:159`). No se puede cumplir
sin una tabla `tasks` con clave foránea a `projects`. Sus columnas están fijadas
por §Tareas v1 (`docs/contrato-api.md:99`): `id`, `title`, `description`,
`project_id`, `state_id`. Ningún documento ata la creación de esa tabla a una
sesión concreta, y el mecanismo (migración de Alembic con `downgrade`) es el
mismo que ya usa el repo para `states`. Se crea la tabla **completa** ahora; la
sesión *Tareas v1* solo añadirá endpoints, y *Tareas v2* añadirá `due_at` por
migración con rollback (`docs/contrato-api.md:163`).

### D2 — `project_id` y `state_id` en `tasks`: `NOT NULL` y FK con `ON DELETE RESTRICT`

El contrato prohíbe el borrado en cascada implícito
(`docs/contrato-api.md:95–96`) y establece que una referencia inexistente no se
crea implícitamente (`docs/contrato-api.md:18`). `RESTRICT` a nivel de base es
la defensa de fondo. La API, además, comprueba la existencia de tareas y
responde `409` con `{"detail": "<mensaje>"}` **antes** de intentar el `DELETE`,
para no filtrar el error del driver (`docs/contrato-api.md:14–17`).

### D3 — Validación de `name`: obligatorio; se recorta y se rechaza vacío con `422`

La normalización por categoría Unicode del contrato está acotada a `title` de
tarea (`docs/contrato-api.md:22`). Para `name` de proyecto aplica solo la
convención general: `422` para entrada inválida (`docs/contrato-api.md:10`). Se
decide: se aplica `strip()` a `name` y se rechaza con `422` si el resultado es
cadena vacía. `description` es opcional, su valor por defecto es `null` y no se
normaliza.

### D4 — `PATCH` parcial: solo cambian los campos presentes en el cuerpo

`docs/contrato-api.md:91` dice *"actualización parcial"*. Se distingue "campo
ausente" de "campo con valor `null`" usando un modelo de entrada con campos
opcionales y `model_dump(exclude_unset=True)`:

- `{"name": "x"}` cambia `name` y no toca `description`.
- `{"description": null}` pone `description` a `null` explícitamente.
- `{"name": ""}` o `{"name": "   "}` → `422` (misma regla que D3).
- `{}` → `200` con el proyecto sin cambios.

### D5 — Modelos de entrada con `extra="forbid"`

Coherente con el espíritu "ni más ni menos" del contrato
(`docs/contrato-api.md:123`) y con `StateOut` (`app/schemas.py:9`), que ya usa
`extra="forbid"`. `POST /projects` con un campo desconocido (p. ej. `state_id`)
→ `422`. Decisión reversible; el contrato no la fija.

### D6 — Esquema de respuesta: `ProjectOut` con `id`, `name`, `description`, y nada más

Modelo Pydantic con `model_config = ConfigDict(from_attributes=True,
extra="forbid")`, igual que `StateOut`. `description` ausente se serializa como
`null` (`docs/contrato-api.md:145`). `response_model=list[ProjectOut]` en la
colección garantiza la lista JSON en la raíz.

### D7 — Orden de `GET /projects`: `ORDER BY projects.id ASC`

`docs/contrato-api.md:41`.

### D8 — Tipos de columna de texto sin longitud fija

`name`, `description` (y `title` de `tasks`) se declaran como `String` sin
longitud (→ `VARCHAR` sin límite en PostgreSQL). El contrato no fija ninguna
longitud máxima; acotarla introduciría un `422` que el contrato no describe.
`states.code` sí usa `String(32)` porque es un catálogo cerrado.

### D9 — Rutas en un `APIRouter` propio

Se crea `app/routers/projects.py` con un `APIRouter` montado desde
`app/main.py`. Cinco rutas de proyectos junto a `health` y `states` dejarían
`app/main.py` ilegible; `APIRouter` es el mecanismo estándar de FastAPI y no
cambia comportamiento observable. `app/main.py` conserva `lifespan`, `/health` y
el registro del router.

### D10 — Aislamiento de tests: se reutiliza el patrón existente

Los tests de `states` aplican `alembic upgrade head` por módulo y `downgrade
base` al terminar, con `pytest.skip` si el PostgreSQL de Compose no responde
(`tests/test_states_endpoint.py:29–47`, `tests/test_migrations_cycle.py`). Los
tests nuevos siguen el mismo patrón. No se introduce `testcontainers` ni se
modifica `tests/conftest.py`.

## Incrementos

### Incremento 1 — Migración de la tabla `projects`

**Objetivo:** crear la tabla `projects` (`id` PK generada por la base, `name`
`NOT NULL`, `description` nullable) mediante una revisión de Alembic con
`downgrade` que la elimina.

**Toca:** `alembic/versions/<rev>_crea_la_tabla_projects.py` (nueva revisión,
`down_revision` = cabeza actual `0b1b461bb5d6`).

**Test que falla primero:** `tests/test_migrations_projects.py` — contra el
PostgreSQL de Compose, siguiendo el patrón de `tests/test_states_seed.py`:

- tras `upgrade head`, `inspect(engine).get_columns("projects")` da exactamente
  `{id, name, description}`; `name.nullable is False`, `description.nullable is
  True`; PK en `("id",)`;
- `downgrade -1` elimina la tabla `projects`;
- `upgrade head` la reconstruye idéntica.

Falla hoy porque la revisión no existe.

**Comprobación:**

```bash
docker compose up -d
docker compose ps                       # 'db' aparece como healthy
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
uv run pytest -q tests/test_migrations_projects.py
uv run pytest -q tests/test_migrations_cycle.py   # sigue verde con una revisión más
uv run ruff check .
```

Éxito: los tests nuevos y el ciclo genérico en verde; `upgrade`/`downgrade` sin
error; la tabla aparece y desaparece con cada sentido.

### Incremento 2 — Migración de la tabla `tasks` (solo esquema)

**Objetivo:** crear la tabla `tasks` (`id` PK, `title` `NOT NULL`, `description`
nullable, `project_id` `NOT NULL` FK → `projects.id` `ON DELETE RESTRICT`,
`state_id` `NOT NULL` FK → `states.id` `ON DELETE RESTRICT`) mediante una
revisión de Alembic con `downgrade` que la elimina. Sin seed y sin endpoints.

**Toca:** `alembic/versions/<rev>_crea_la_tabla_tasks.py` (`down_revision` = la
revisión del Incremento 1).

**Test que falla primero:** `tests/test_migrations_tasks.py` —

- tras `upgrade head`, columnas exactas `{id, title, description, project_id,
  state_id}` (sin `due_at`); nullability según lo anterior; PK en `("id",)`;
- `get_foreign_keys("tasks")` incluye una FK `project_id → projects(id)` y otra
  `state_id → states(id)`, ambas con regla de borrado `RESTRICT`;
- `downgrade -1` elimina `tasks` y deja `projects` y `states` intactas.

Falla hoy porque la revisión no existe.

**Comprobación:**

```bash
docker compose up -d
uv run alembic upgrade head
uv run alembic downgrade -1              # revierte solo 'tasks'
uv run alembic upgrade head
uv run pytest -q tests/test_migrations_tasks.py
uv run pytest -q tests/test_migrations_cycle.py
uv run ruff check .
```

Éxito: FKs verificadas por introspección con la regla `RESTRICT`; el ciclo
completo `upgrade head` → `downgrade base` → `upgrade head` sin error.

### Incremento 3 — `POST /projects` y `GET /projects`

**Objetivo:** crear un proyecto (`201` con el recurso) y listar los proyectos
(`200`, lista JSON en la raíz, orden por `id` ascendente), con el esquema exacto
del contrato.

**Toca:** `app/models.py` (modelo `Project` mapeado a `projects`, solo describe
la tabla existente), `app/schemas.py` (`ProjectCreate` con `extra="forbid"`,
`ProjectOut`), `app/routers/projects.py` (nuevo `APIRouter`), `app/main.py`
(`app.include_router(...)`), `README.md` (mención de que `/projects` existe).

**Test que falla primero:** `tests/test_projects_crud.py` —

- `test_post_crea_devuelve_201_y_esquema_exacto`: `POST {"name": "Casa"}` →
  `201`, cuerpo con exactamente las claves `{id, name, description}` y
  `description` a `null`;
- `test_post_con_description`: se guarda y se devuelve;
- `test_post_sin_name_es_422` y `test_post_name_en_blanco_es_422`: clave de
  primer nivel `detail`;
- `test_post_campo_desconocido_es_422` (D5);
- `test_get_lista_en_la_raiz_y_ordenada_por_id`: crea tres proyectos, `GET
  /projects` devuelve una lista (no un objeto), con los `id` en orden ascendente
  y estable entre dos llamadas idénticas.

Fallan hoy porque no hay endpoints ni modelo.

**Comprobación:**

```bash
docker compose up -d
uv run alembic upgrade head
uv run pytest -q tests/test_projects_crud.py
uv run ruff check .

# Manual, con la API servida (uv run uvicorn app.main:app):
curl -s -i -X POST localhost:8000/projects \
  -H 'content-type: application/json' -d '{"name":"Casa"}'
#   → 201  {"id":1,"name":"Casa","description":null}
curl -s -X POST localhost:8000/projects \
  -H 'content-type: application/json' -d '{"name":"   "}'
#   → 422  {"detail": ...}
curl -s localhost:8000/projects
#   → [{"id":1,"name":"Casa","description":null}]   (lista en la raíz)
```

Éxito: los tests en verde; `POST` válido devuelve 3 claves exactas; `POST`
inválido devuelve `422` con clave raíz `detail`; `GET` devuelve lista JSON
ordenada por `id`.

### Incremento 4 — `GET /projects/{id}` y `PATCH /projects/{id}`

**Objetivo:** leer un proyecto por `id` (`200`, o `404` si no existe) y
actualizarlo parcialmente (`200`, solo los campos enviados; `404` si no existe).

**Toca:** `app/routers/projects.py`, `app/schemas.py` (`ProjectUpdate`: `name` y
`description` opcionales, `extra="forbid"`), `tests/test_projects_crud.py`.

**Test que falla primero:**

- `test_get_por_id_existente_200_esquema_exacto`;
- `test_get_por_id_inexistente_404` (cuerpo con clave `detail`);
- `test_get_por_id_no_entero_422` (la conversión de ruta de FastAPI);
- `test_patch_cambia_solo_lo_enviado`: `PATCH {"description": "con jardín"}` deja
  `name` intacto;
- `test_patch_description_a_null`;
- `test_patch_cuerpo_vacio_200_sin_cambios`;
- `test_patch_name_en_blanco_422`;
- `test_patch_id_inexistente_404`.

**Comprobación:**

```bash
uv run pytest -q tests/test_projects_crud.py
uv run ruff check .

curl -s -i localhost:8000/projects/999
#   → 404  {"detail": ...}
curl -s -X PATCH localhost:8000/projects/1 \
  -H 'content-type: application/json' -d '{"description":"con jardín"}'
#   → 200  name sin cambios, description actualizada
curl -s -X PATCH localhost:8000/projects/1 \
  -H 'content-type: application/json' -d '{}'
#   → 200  proyecto sin cambios
```

Éxito: todos los tests en verde; `PATCH` solo modifica los campos presentes en
el cuerpo; `404` para `id` inexistente en `GET` y `PATCH`.

### Incremento 5 — `DELETE /projects/{id}` con `204` / `409`

**Objetivo:** borrar un proyecto sin tareas (`204`, sin cuerpo) y rechazar con
`409` el borrado de un proyecto que tiene tareas, sin cascada.

**Toca:** `app/routers/projects.py`, `tests/test_projects_delete.py`.

**Implementación prevista:** la ruta ejecuta `SELECT 1 FROM tasks WHERE
project_id = :id LIMIT 1`; si hay fila → `409` con `{"detail": "<mensaje>"}` y
el proyecto permanece; si no hay fila → `DELETE` y `204` sin cuerpo; si el
proyecto no existe → `404`. La FK `ON DELETE RESTRICT` del Incremento 2 es la
red de seguridad. En los tests, como no hay endpoint de tareas, las filas de
`tasks` se insertan directamente con un `state_id` del catálogo ya sembrado.

**Test que falla primero:** `tests/test_projects_delete.py` —

- `test_delete_sin_tareas_devuelve_204_sin_cuerpo`;
- `test_delete_id_inexistente_404`;
- `test_delete_con_tareas_devuelve_409`;
- `test_delete_con_tareas_no_borra_el_proyecto` (tras el `409`, `GET
  /projects/{id}` sigue devolviendo `200`);
- `test_delete_no_borra_en_cascada` (las filas de `tasks` siguen presentes tras
  el `409`).

**Comprobación:**

```bash
docker compose up -d
uv run alembic upgrade head
uv run pytest -q tests/test_projects_delete.py
uv run pytest -q                         # suite completa en verde
uv run ruff check .

curl -s -i -X DELETE localhost:8000/projects/1
#   → 204  sin cuerpo   (proyecto sin tareas)
```

Éxito: `204` sin cuerpo cuando no hay tareas; `409` con clave raíz `detail`
cuando las hay, con el proyecto y sus tareas intactos; `404` si el `id` no
existe; suite completa en verde.

### Incremento 6 — Repaso de la Matriz Mínima y cierre operativo

**Objetivo:** verificar que la suite cubre las filas de la Matriz Mínima que
tocan proyectos y dejar `README.md` al día.

**Toca:** `README.md` (recorrido y lista de endpoints disponibles), y solo
tests si se detecta un hueco de cobertura.

**Comprobación:** repaso explícito contra `docs/contrato-api.md:152–167`:

- *CRUD feliz de proyectos* → Incrementos 3–5.
- *IDs inexistentes* → `404` en `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`.
- *Borrado de proyecto con tareas (`409`)* → Incremento 5.
- *Orden estable: dos llamadas idénticas devuelven los `id` en la misma
  posición* → Incremento 3.
- *Esquema de respuesta exacto: los campos declarados, ni uno más* →
  Incrementos 3–4 (`ProjectOut` con `extra="forbid"`).
- *Migración desde base vacía* → el ciclo genérico de
  `tests/test_migrations_cycle.py` cubre ahora `projects` y `tasks`.

```bash
uv run pytest -q
uv run ruff check .
```

Éxito: suite completa en verde, `ruff` limpio, y cada fila de la Matriz Mínima
relativa a proyectos tiene al menos un test que la ejercita.

## Reglas de ejecución

- **Un incremento = un commit**, confirmado **solo** con su sección
  *Comprobación*. El mensaje de commit se muestra antes de crearlo.
- Al terminar un incremento, **parar y esperar aprobación**. No encadenar el
  siguiente.
- Una capacidad nueva **empieza por un test que falla** por su ausencia.
- **No se debilita ni se elimina** un test existente para conseguir verde. Si el
  comportamiento acordado cambiara, se edita antes `docs/contrato-api.md` y
  después el test, en un commit separado y previo.
- Cada migración implementa `upgrade` y `downgrade` y se prueba **en ambos
  sentidos** antes de integrarse. El esquema no se crea por efectos de
  importación de módulos.
- No se abre, muestra, edita ni confirma `.env`. `.env.example` es la única
  fuente permitida para nombres de variables.
- Los tests de persistencia corren contra el PostgreSQL real de `compose.yaml`;
  si la base no está disponible se marcan `skipped`, no se adaptan a SQLite.
