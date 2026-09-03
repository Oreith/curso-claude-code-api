---
name: planificar-incremento
description: >-
  Redacta el plan de un incremento de trabajo para este repositorio, contra los
  documentos rectores, con incrementos numerados y comprobación ejecutable cada
  uno. Úsala cuando haya que planificar una capacidad nueva antes de tocar
  código. Planifica; no implementa.
---

# planificar-incremento

Produce un plan de trabajo escrito. No implementa nada.

## Contra qué se planifica

Lee, antes de escribir una sola línea del plan, estos documentos del repositorio:

- **`docs/contrato-api.md`** — comportamiento observable vinculante: códigos de
  estado, esquemas de respuesta "ni más ni menos", orden de las listas,
  normalización de `title`, serialización de `due_at`, y la Matriz Mínima de
  Tests. Manda sobre el código. No se modifica salvo que el ticket lo diga
  explícitamente.
- **`docs/decisiones-ingenieria.md`** — decisiones de proceso, base de datos y
  pruebas que pertenecen al equipo y no se deducen del código.
- **`docs/onboarding.md`** — briefing con Hechos / Inferencias / Desconocidos y,
  en §5, la lista de decisiones aún sin tomar. Consúltalo antes de asumir cómo
  está resuelta la persistencia.
- **`CLAUDE.md`** — límites de trabajo y comandos canónicos.
- **`README.md`** — requisitos y comandos de operación.
- Los planes ya existentes en `docs/` (p. ej. `docs/plan-persistencia.md`) como
  referencia de formato y de alcance ya cubierto.

Si un documento citado por otro no existe en el repositorio, decláralo como
hueco; no lo des por supuesto.

## Dónde va el resultado

Un único archivo Markdown nuevo en **`docs/`**, con un nombre que diga de qué es
el plan: `docs/plan-<tema>.md` (por ejemplo `docs/plan-projects.md`,
`docs/plan-tareas-v2.md`). No se escribe el plan en el chat como entregable
final ni en ningún otro directorio.

## Forma del plan

El archivo contiene, en este orden:

1. **Título y estado** — `Estado: propuesto, pendiente de aprobación`.
2. **Fuentes** — la lista de documentos y secciones concretas contra las que se
   planifica.
3. **Alcance** — en una o dos frases, hasta dónde llega este plan.
4. **Fuera de alcance** — lista explícita de lo que este plan **no** aborda.
   Nunca se deja implícito.
5. **Incrementos numerados** — `Incremento 1`, `Incremento 2`, … Cada uno:
   - un objetivo de una frase;
   - los archivos o áreas que toca;
   - una sección **Comprobación** con los comandos exactos que otra persona
     ejecutaría para verificarlo (`uv run pytest -q ...`, `uv run ruff check .`,
     `uv run alembic upgrade head`, `curl ...`), y el criterio de éxito;
   - la regla de que una capacidad nueva empieza por un test que falla por su
     ausencia.
6. **Reglas de ejecución** — un incremento = un commit, confirmado solo con su
   comprobación; parar y esperar aprobación entre incrementos; no debilitar
   tests para conseguir verde; si el contrato cambia, se edita antes que el
   test, en commit separado.

## Ninguna decisión aplazada

El plan no contiene recomendaciones en condicional ni tablas de "opciones a
evaluar". Para cada decisión de ingeniería que el plan necesite:

- si se puede resolver con lo que hay en el repositorio (documentos, código,
  `uv.lock`, historial), se **decide** en el plan y se cita la evidencia;
- si **no** se puede resolver con lo que hay, se **pregunta al usuario** de
  forma directa antes de cerrar el plan, y el plan no avanza sobre esa decisión
  hasta tener respuesta.

Revisa `docs/onboarding.md` §5 para las decisiones ya identificadas como
abiertas y trátalas así.

## Límite: planificar, no implementar

Esta skill **solo** escribe el archivo de plan en `docs/`. Mientras se ejecuta:

- no crea ni modifica código de la aplicación, tests, migraciones ni
  configuración;
- no edita `pyproject.toml` ni `uv.lock`, y no instala ni actualiza
  dependencias;
- no ejecuta migraciones ni ninguna operación contra la base de datos;
- no toca los documentos rectores (`docs/contrato-api.md`,
  `docs/decisiones-ingenieria.md`, `CLAUDE.md`, `README.md`).

Los comandos de comprobación se **escriben** en el plan; no se ejecutan aquí.
