---
name: segmentar-commits
description: >-
  Reparte trabajo ya hecho pero sin confirmar en una secuencia de commits con
  una sola intención cada uno, en un orden en el que cada commit deja el
  repositorio comprobable. Empieza por el estado real del repo. Propone el
  reparto y espera aprobación antes de confirmar nada.
argument-hint: "[pista opcional de agrupación, p. ej. 'por incremento del plan']"
allowed-tools: >-
  Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git add:*),
  Bash(git commit:*), Bash(git reset:*), Bash(git restore:*), Bash(git stash:*)
---

# segmentar-commits

Toma los cambios que hay en el árbol de trabajo y los reparte en commits. No
implementa nada, no arregla nada.

## Estado real del repositorio (en el momento de invocar)

- Rama y archivos tocados: !`git status --short --branch`
- Magnitud del cambio por archivo (lo que tiene seguimiento): !`git diff --stat HEAD`
- Últimos commits: !`git log --oneline -8`

Ese bloque es la verdad de partida. **No planifiques el reparto contra lo que la
conversación dice que se hizo**: planifícalo contra esa salida. Si hay conflicto
entre lo que recuerdas y lo que muestra `git status`, gana `git status`.

Los archivos con `??` en `git status` son nuevos y no aparecen en `git diff
--stat`. Cuéntalos como archivos completos. Si necesitas su tamaño, `wc -l
<ruta>`; no abras su contenido salvo que el corte lo exija.

## Qué leer antes de proponer

Solo lo que haga falta para decidir fronteras:

- el contenido de los archivos o *hunks* cuya asignación a un commit no sea
  obvia por el nombre y el `--stat`;
- `git log --oneline -15` y algún commit reciente si necesitas imitar el estilo
  de mensajes del repositorio (prefijos, idioma, scope, *trailers*).

No leas el diff completo entero. El mapa (`--short` + `--stat`) más lecturas
puntuales basta.

## Una intención por commit

Una **intención** es un cambio que se explica en una frase sin la palabra "y":
"expone `GET /projects`", "migra la tabla `tasks`", "corrige el desbordamiento
al truncar", "adapta el test del ciclo a más de una revisión".

- Agrupa por lo que el cambio **consigue**, no por el archivo. Un mismo archivo
  puede repartirse entre commits tomando sus *hunks* con `git add -p`; varios
  archivos pueden ir en un commit si sirven a la misma intención (código + su
  test + la línea de README que lo documenta).
- Un refactor o un movimiento de código va **separado** de un cambio de
  comportamiento, aunque toquen el mismo archivo.
- Si un cambio obligó a tocar un test existente (una referencia frágil que se
  rompe al añadir código, no un cambio de contrato), esa adaptación va en su
  propio commit `test:` **antes** del commit que la fuerza, o dentro de ese
  mismo commit. Nunca en una posición que deje un commit intermedio en rojo.
- Ruido inevitable (p. ej. `uv.lock` regenerado) va con el commit que lo causa,
  mencionado en el cuerpo.

## Orden comprobable

Ordena los commits de modo que, aplicados uno a uno, **cada commit deje el
repositorio en un estado que otra persona pueda comprobar**:

- lo que se importa antes que lo que lo usa: migraciones y esquema antes del
  código que consulta esas tablas; *helpers* compartidos antes de sus
  consumidores;
- ningún commit intermedio deja la suite peor que antes de la serie. Un corte
  que dejaría `uv run pytest -q` en rojo es un corte mal hecho: reagrupa o
  reordena.
- para cada commit, escribe la **Comprobación**: el comando exacto que lo
  valida (`uv run pytest -q ...`, `uv run ruff check .`, `uv run alembic upgrade
  head` / `downgrade base`, `curl ...`) y el criterio de éxito.

## Conventional Commits: el prefijo lo fija la intención

`<tipo>(<scope opcional>): <resumen en imperativo>`. El resumen, ≤ ~72
caracteres; el cuerpo explica el porqué si no es evidente.

El tipo describe **qué hace el commit**, no qué clase de archivo toca:

- `feat` — capacidad observable nueva. Un commit que añade un endpoint **con**
  sus tests **y** una línea de README sigue siendo `feat`, no se parte en tres
  ni se llama `docs`.
- `fix` — corrige comportamiento incorrecto.
- `refactor` — reorganiza sin cambiar comportamiento observable.
- `test` — solo toca tests (añade cobertura, adapta una referencia frágil).
- `docs` — solo documentación.
- `chore` — tooling, configuración, dependencias sin efecto en la app.
- `perf`, `build`, `ci` — si aplican y el repo ya los usa.

Ante duda entre `feat` y `refactor`: si el `docs/contrato-api.md` o un test de
comportamiento cambia de resultado, es `feat`/`fix`.

## Propón y espera aprobación

Antes de tocar el índice, presenta el reparto como una tabla:

| # | Prefijo y mensaje | Archivos (marca los que necesitan `git add -p`) | Comprobación |
|---|---|---|---|

Debajo, el cuerpo completo de cada mensaje si lleva más de una línea.

**Para y espera la aprobación explícita del usuario.** No ejecutes ningún `git
add` ni `git commit` hasta que diga "adelante" / "confírmalos así" / equivalente.
El usuario puede reordenar, fusionar o reescribir mensajes; incorpora sus
cambios y, si el reparto cambia de forma, vuelve a enseñarlo.

## Al confirmar

Una vez aprobado, y solo entonces:

1. Haz los commits **uno a uno, en el orden acordado**.
2. Para cada uno: arma el commit **solo con `git add`** sobre el cambio que ya
   está en el árbol —archivos completos, o `git add -p` para tomar *hunks*
   sueltos (si un archivo sin seguimiento hay que repartirlo, `git add -N` y
   luego `git add -p`)—. **Nunca edites un archivo para dar forma a un commit
   ni para reconstruir un estado intermedio**: esta skill no toca una sola
   línea de código. Enseña el mensaje final, `git commit`, y ejecuta su
   **Comprobación** antes de pasar al siguiente.
3. Respeta los *trailers* de commit que el entorno de la sesión indique
   (autoría, `Co-Authored-By`, enlace de sesión).
4. Si una Comprobación falla, **detente**: no sigas con el resto de commits.
   Informa de qué commit quedó en rojo y con qué salida, y deja que el usuario
   decida (`git reset --soft HEAD~1`, corregir, reordenar).

## Límite

Esta skill reparte y confirma trabajo **ya presente en el árbol**. No:

- escribe código, tests, migraciones ni documentación nueva;
- edita ningún archivo para armar un commit: cada commit se compone
  **exclusivamente con `git add`** (completo o `-p`) sobre lo que ya hay en el
  árbol, sin reescribir ni una línea;
- arregla una suite que ya estaba en rojo antes de invocarla (dilo y detente);
- reescribe, reordena (`rebase`) ni fusiona commits ya existentes;
- hace `push` ni abre PR.

Si al invocarla el árbol está limpio (`git status --short` sin salida), dilo y
no hagas nada más.
