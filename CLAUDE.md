# CLAUDE.md

## Fuentes de verdad

Mandan sobre el código. Ante conflicto, gana el documento.

- **Comportamiento observable** — `docs/contrato-api.md`. Códigos de estado,
  esquemas de respuesta ("ni más ni menos") y ordenamientos son vinculantes.
  Solo se modifica cuando el ticket lo dice explícitamente, y antes que el
  código o los tests.
- **Decisiones de ingeniería** (proceso, base de datos, pruebas) —
  `docs/decisiones-ingenieria.md`.
- **Operación** (requisitos y comandos) — `README.md`.
- **Contexto de arranque** (Hechos / Inferencias / Desconocidos, decisiones sin
  tomar) — `docs/onboarding.md`. Consúltalo antes de asumir cómo está resuelta
  la persistencia.

## Comandos canónicos

```bash
uv sync --frozen        # instalar dependencias exactas de uv.lock
uv run pytest -q         # tests
uv run ruff check .      # lint (sin autofix configurado)
```

Ruff aplica `E, F, I, UP, B` con `line-length = 88`. `pytest` corre sobre
`tests/`. Recorrido completo (Docker, servidor) en `README.md`.

## Al implementar

- Antes de tocar cualquier endpoint, lee las secciones **Esquemas de Respuesta**
  y **Orden de las listas** de `docs/contrato-api.md`.
- Endpoints y campos: esquema de respuesta exacto del contrato, y un campo nuevo
  son tres capas (migración, esquema, validación). Rutas de las carpetas y el
  ejemplo `priority` en `.claude/rules/api-conventions.md`.
- Normalización de `title`: no basta `strip()`; hay que rechazar con `422` por
  categoría Unicode `Cc, Cf, Zl, Zp, Zs` (ver `docs/contrato-api.md`).
- `due_at` se serializa en UTC con sufijo `Z` (no `+00:00`) y sin microsegundos.

## Persistencia

- Las pruebas de persistencia corren contra **PostgreSQL real, no SQLite**.
- El esquema cambia mediante migraciones de Alembic con `upgrade`/`downgrade`,
  probadas en ambos sentidos; nunca por efectos de importación de módulos.
- Decisiones aún abiertas (ORM, driver, aislamiento de tests) en
  `docs/onboarding.md` §5: confírmalas con el usuario antes de elegir.

## Pruebas

- Una capacidad nueva empieza por un test que falla por su ausencia.
- No debilites ni elimines un test existente para conseguir verde. Si el
  comportamiento acordado cambió, edita antes el contrato y luego el test, en un
  commit separado.
- Fallos reportados: se reproducen antes de corregirlos y la reproducción se
  conserva. Ver `.claude/rules/testing.md`.

## Reparto de commits

- Repartir o reorganizar cambios del árbol en commits (p. ej. la skill
  `segmentar-commits`) nunca reescribe código para simular un estado
  intermedio: solo `git add`, completo o con `git add -p`. Ver
  `.claude/rules/code-style.md`.

## Secretos

- No abras, muestres, edites ni confirmes `.env`.
- `.env.example` es la única fuente permitida para los nombres de variables. Los
  valores reales se configuran fuera de la conversación.
- Nunca pongas credenciales reales en `.env.example` ni en `compose.yaml`.
