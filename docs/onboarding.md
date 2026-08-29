# Onboarding — TaskFlow API (`curso-claude-code-api`)

Briefing del repositorio. Todas las citas apuntan a archivo y línea del repo.
Se separan **Hechos** (verificables en el repo), **Inferencias** (deducciones
razonadas) y **Desconocidos** (sin evidencia).

Estado a fecha 2026-08-28: rama `main`, dos commits, solo `GET /health`
implementado.

---

## 1. Fuente de verdad del comportamiento

### Hechos

- El documento normativo es **`docs/contrato-api.md`**. Se autodeclara como tal:
  *"Este documento fija comportamiento observable"* (`docs/contrato-api.md:3`) y
  *"Los códigos de las tablas siguientes son parte del contrato: son lo que
  afirman los tests, y lo que la sesión 10 compara al revisar. No los cambies sin
  cambiar antes este documento."* (`docs/contrato-api.md:11-13`).
- El contrato fija: convenciones JSON/fechas/IDs/códigos de error
  (`docs/contrato-api.md:7-18`), forma estable de errores
  `{"detail": "<mensaje>"}` (`docs/contrato-api.md:14-17`), normalización de
  `title` con rechazo por categoría Unicode `Cc, Cf, Zl, Zp, Zs`
  (`docs/contrato-api.md:20-31`), orden determinista de cada colección
  (`docs/contrato-api.md:33-42`), esquemas de respuesta exactos "ni más ni menos"
  (`docs/contrato-api.md:121-150`) y una matriz mínima de tests
  (`docs/contrato-api.md:152-167`).
- Lo único implementado hoy es `GET /health` -> `200` con `{"status": "ok"}`
  (`app/main.py:6-8`; contrato en `docs/contrato-api.md:46-52`; `README.md:34`).
- La **estructura interna queda abierta** salvo restricciones de seguridad,
  migración y verificación (`docs/contrato-api.md:3-5`).
- `README.md` es la fuente de verdad **operativa** (requisitos y comandos):
  `README.md:6-32`.
- No existe `CLAUDE.md` ni otros documentos de reglas (verificado: `ls`, sin
  resultados).

### Inferencias

- El contrato menciona "sesión 7", "sesión 10", "sesión 11/glosario" y "el curso
  adopta X": es material de un curso con entregas incrementales. El estado actual
  es la entrega base (solo `/health`).
- Ante conflicto entre código/tests y `docs/contrato-api.md`, gana el contrato
  (lo dice explícitamente en `docs/contrato-api.md:11-13` y `:167`: *"No pueden
  debilitar estas invariantes"*).

### Desconocidos

- `docs/contrato-api.md:79` enlaza `../docs/glosario.md#idempotente`, **que no
  existe** en el repo. No hay definición local de "idempotente".
- No hay especificación OpenAPI escrita a mano; la que exista será la autogenerada
  por FastAPI (no verificable como "fuente de verdad").

---

## 2. Comandos exactos

### Hechos — de `README.md:12-32`

| Acción | Comando | Cita |
|---|---|---|
| Instalar dependencias (fijadas) | `uv sync --frozen` | `README.md:16` |
| Ejecutar tests | `uv run pytest -q` | `README.md:19` |
| Revisar estilo | `uv run ruff check .` | `README.md:22` |
| Levantar PostgreSQL (background) | `docker compose up -d` | `README.md:25` |
| Servir la API en local | `uv run uvicorn app.main:app --reload` | `README.md:28` |
| Parar y retirar contenedores | `docker compose down` | `README.md:31` |

- La API sirve en `http://127.0.0.1:8000` (`README.md:27-28`).
- `pytest` está configurado con `testpaths = ["tests"]` (`pyproject.toml:29-30`).
- Ruff: `target-version = "py312"`, `line-length = 88`, reglas
  `["E", "F", "I", "UP", "B"]` (`pyproject.toml:22-27`).
- Requisitos: Python serie 3.12, uv, Docker con Compose v2 (`README.md:8-10`);
  `requires-python = ">=3.12,<3.13"` (`pyproject.toml:6`).

### Inferencias

- No hay comando de "detener el servidor uvicorn" documentado; se detiene con
  `Ctrl-C` en su terminal (proceso en foreground con `--reload`).
- `docker compose down` **no** borra el volumen `postgres_data`
  (`compose.yaml:18-19`); para eso haría falta `docker compose down -v` (no
  documentado, no verificado como intención).
- No hay comando de migraciones todavía: el contrato adopta migración
  (`docs/contrato-api.md:73-77`) pero no hay herramienta (Alembic u otra) en
  `pyproject.toml:7-17`.

### Desconocidos

- Herramienta de migración concreta y su comando (`alembic upgrade head` u otro):
  **sin evidencia**.
- Comando para lint con autofix (`ruff check --fix`): no documentado.
- Ejecución de la app dentro de Docker: `compose.yaml:1-16` solo define el
  servicio `db`, no la API.

---

## 3. Motor para los futuros tests de persistencia

### Hechos

- El contrato adopta **migración** como mecanismo de seed del catálogo de estados,
  y descarta el script de inicialización de Docker: *"El curso adopta la
  migración. Con el script de Docker, quien ya tenía el volumen creado nunca
  recibe el catálogo"* (`docs/contrato-api.md:69-77`).
- El seed debe ser **idempotente**: *"ejecutarlo dos veces deja lo mismo que
  una"* (`docs/contrato-api.md:79-80`).
- La matriz de tests exige: *"Migración desde base vacía y rollback de v2"* y *"El
  catálogo de estados existe tras migrar, y migrar dos veces no lo duplica"*
  (`docs/contrato-api.md:163-164`).
- El motor de base de datos es **PostgreSQL 18** (`compose.yaml:3`:
  `image: postgres:18-alpine`), con credenciales por defecto
  `taskflow` / `taskflow_local` / db `taskflow` en puerto `5432`
  (`compose.yaml:5-9`, `.env.example:2-5`).
- IDs = enteros positivos **generados por la base** (`docs/contrato-api.md:9`).

### Inferencias

- "Motor que deben usar los tests de persistencia" = los tests deben correr contra
  **PostgreSQL real** (el mismo `postgres:18-alpine` de `compose.yaml`), no SQLite
  en memoria, porque:
  - El contrato exige probar migraciones y rollback (`docs/contrato-api.md:163`),
    que dependen del dialecto.
  - Los IDs los genera la base (`docs/contrato-api.md:9`).
  - La normalización Unicode y el orden estable se afirman como comportamiento
    observable end-to-end.
- El "motor" de migraciones probablemente será Alembic (estándar de facto con
  FastAPI/SQLAlchemy), pero **no está elegido en el repo**.

### Desconocidos

- ORM / capa de acceso a datos (SQLAlchemy, SQLModel, asyncpg puro): **no hay
  dependencia declarada** (`pyproject.toml:7-10` solo tiene `fastapi` y
  `uvicorn`).
- Herramienta de migraciones concreta: sin evidencia.
- Estrategia de aislamiento entre tests (transacción con rollback, base efímera,
  `testcontainers`): sin evidencia.
- Si los tests usan una base separada de la de desarrollo: sin evidencia.
- Driver (sync `psycopg` vs async `asyncpg`): sin evidencia.

---

## 4. Límites sobre archivos con secretos

### Hechos

- `.env` **está en `.gitignore`** (`.gitignore:1`) — no debe versionarse.
- Sin embargo, **`.env` sí está presente en el working tree** y es **idéntico a
  `.env.example`** (`.env:1-6` == `.env.example:1-6`), conteniendo solo valores
  locales de desarrollo (`POSTGRES_PASSWORD=taskflow_local`). No aparece en
  `git log --stat` de ningún commit -> nunca fue commiteado.
- El proyecto **arranca sin `.env`**: *"`compose.yaml` trae valores locales por
  defecto, así que arranca sin `.env`"* (`README.md:38-40`; defaults en
  `compose.yaml:5-9` vía `${VAR:-default}`).
- El flujo previsto: *"copia `.env.example` a `.env` y ajusta..."*
  (`README.md:39-40`, `.env.example:1`).
- El contrato prohíbe filtrar secretos por la API: `GET /health` *"No expone
  credenciales ni detalles internos"* (`docs/contrato-api.md:54`); errores *"con
  forma estable"* sin detalles internos (`docs/contrato-api.md:14-17`).
- La healthcheck de Compose referencia variables con escape `$$` para que las
  resuelva el contenedor, no Compose (`compose.yaml:13`).

### Inferencias

- **Límite operativo**: nunca commitear `.env`; cualquier secreto real
  (contraseñas no-locales, credenciales de CI/despliegue) va solo en `.env` local
  o en el gestor de secretos del entorno, nunca en `.env.example` ni en
  `compose.yaml`.
- `.env.example` es plantilla pública: solo debe contener placeholders / valores
  de desarrollo inocuos, como ahora.
- Los valores actuales (`taskflow_local`) son de desarrollo; no son secretos
  reales, pero el archivo `.env` no debe editarse para incluir credenciales
  reales y luego arriesgar un `git add -f`.

### Desconocidos

- Si existe CI con secretos configurados: no hay `.github/`, `.gitlab-ci.yml` ni
  similar en el repo.
- Política de secretos para producción/despliegue: sin evidencia.
- Si `ANTHROPIC_API_KEY` u otras claves del curso deben vivir aquí: sin evidencia
  (no se mencionan).

---

## 5. Decisiones que no puedo establecer con evidencia

Requieren confirmación antes de implementar:

1. **Herramienta de migraciones**: el contrato exige migraciones con
   `upgrade`/rollback (`docs/contrato-api.md:73-77`, `:163`) pero no hay ninguna
   dependencia ni configuración. ¿Alembic?
2. **Capa de persistencia / ORM**: sin dependencia declarada
   (`pyproject.toml:7-10`). ¿SQLAlchemy 2.x? ¿SQLModel? ¿sync o async?
3. **Driver de PostgreSQL**: `psycopg` (v3) vs `asyncpg`. Sin evidencia.
4. **Estrategia de test de persistencia**: base dedicada de test, aislamiento por
   transacción/rollback, o contenedor efímero. Sin evidencia.
5. **`glosario.md` faltante**: `docs/contrato-api.md:79` enlaza
   `../docs/glosario.md#idempotente` que no existe. ¿Crearlo, o corregir el
   enlace?
6. **`.env` en el working tree**: existe una copia igual a `.env.example`. ¿Se
   deja (conveniencia local) o se elimina para forzar el flujo "copia el
   example"?
7. **Ejecución de la API en Docker**: `compose.yaml` solo define `db`. ¿La API se
   ejecuta siempre en host con uvicorn, o se añadirá un servicio `api` al compose?
8. **Framework de la forma `422`**: el contrato admite "la forma que genere tu
   framework" con clave raíz `detail` (`docs/contrato-api.md:14-17`). Con FastAPI
   el `422` por defecto es una lista bajo `detail` — asumir que se acepta tal
   cual, pero conviene confirmarlo.
9. **Seed del catálogo de estados**: el catálogo
   (`PENDIENTE, EN_CURSO, BLOQUEADA, HECHA`, `docs/contrato-api.md:58`) se siembra
   en una migración idempotente; falta decidir la técnica (`INSERT ... ON
   CONFLICT` u otra).
10. **Normalización de `due_at`**: el contrato la fija (UTC, sufijo `Z`, sin
    microsegundos — `docs/contrato-api.md:144-148`); la decisión abierta es
    *dónde* se aplica (serializador Pydantic vs. capa de repositorio).
