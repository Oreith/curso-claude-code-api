---
name: describir-esquema
description: >-
  Describe el esquema real de la base de datos de este repositorio en un único
  documento: un diagrama de tablas y relaciones más un diccionario de datos por
  columna. Parte de los modelos y las migraciones tal como están al invocarla.
  Describe; no toca modelos, migraciones, el contrato ni la base.
allowed-tools: >-
  Bash(ls:*), Bash(cat:*), Bash(git log:*), Bash(git diff:*), Read, Grep, Glob, Write
---

# describir-esquema

Produce un solo archivo, `docs/esquema.md`, que describe el esquema de la base
tal como lo definen los modelos y las migraciones **ahora**. No modifica nada.

## Estado real del repositorio (en el momento de invocar)

- Modelos ORM: !`ls -1 app/models.py app/**/models.py 2>/dev/null`
- Migraciones, en orden de aplicación: !`ls -1 alembic/versions/*.py`
- Cadena de revisiones (revisión → padre): !`grep -H -E "^(revision|down_revision):" alembic/versions/*.py`
- Última vez que se tocó cada uno: !`git log -1 --format="%h %ad %s" --date=short -- app/models.py; git log -1 --format="%h %ad %s" --date=short -- alembic/versions/`

Ese bloque es la verdad de partida. Si un modelo o una migración no aparece
ahí, no existe para esta skill. Si la conversación dice que hay una tabla que
esos archivos no definen, gana el archivo.

## Qué leer antes de escribir

1. **Todas** las migraciones de `alembic/versions/`, en el orden que fija la
   cadena `down_revision` (no el orden alfabético del directorio). El esquema
   es el resultado acumulado de aplicarlas en ese orden: una columna añadida
   por `op.add_column`, una constraint creada aparte, un `downgrade` que revela
   el orden de borrado — todo eso es parte del esquema real.
2. **`app/models.py`** (y cualquier otro módulo de modelos que liste el bloque
   de arriba). Los modelos describen tablas que ya existen; donde un modelo y
   una migración discrepen, la **migración manda** (es lo que se aplica a la
   base) y la discrepancia se anota.
3. **`docs/contrato-api.md`**, solo para saber qué **no** repetir (ver abajo).

No hace falta leer los routers, los tests ni los esquemas Pydantic: esta skill
describe la base, no la API.

## Qué inyecta el bloque de estado, y por qué solo eso

El bloque de arriba trae **la lista de archivos, su orden de aplicación y su
antigüedad**, no su contenido. El contenido se lee con `Read` en el paso
anterior, archivo por archivo. El motivo:

- **El orden importa más que el texto.** El esquema real no es ningún archivo
  suelto: es lo que queda tras aplicar las migraciones en secuencia. Inyectar
  `cat` de cada una las mezclaría sin decir cuál va antes; la cadena
  `revision → down_revision` sí fija ese orden y cabe en una línea por archivo.
- **Volcar todo el contenido en el arranque lo congela.** Si la skill se
  invoca dentro de una sesión que acaba de editar una migración, el `cat`
  inyectado podría venir de una versión previa; un `Read` explícito por archivo
  lee el estado del disco en ese momento.
- **La antigüedad marca dónde mirar con cuidado.** Si `app/models.py` se tocó
  después que la última migración, es señal de una posible discrepancia
  modelo/migración que hay que resolver a favor de la migración.

## Forma de `docs/esquema.md`

Un único archivo Markdown nuevo en `docs/`. Contiene, en este orden:

1. **Título y nota de alcance** — una frase: describe el esquema físico
   (tablas, columnas, tipos, claves, constraints) que producen las migraciones
   de `alembic/versions/`; para el comportamiento observable de la API, enlaza
   a `docs/contrato-api.md`.
2. **Diagrama** — las tablas y sus relaciones en un bloque ```mermaid
   `erDiagram`. Una entidad por tabla con sus columnas y tipos; una arista por
   clave foránea, con la cardinalidad y la regla `ON DELETE`. Mermaid se
   versiona como texto, se diferencia en un commit línea a línea, y GitHub lo
   renderiza en el propio archivo sin herramientas.
3. **Diccionario de datos** — una sección por tabla, y dentro una tabla
   Markdown con **una fila por columna**:

   | Columna | Tipo | Nulos | Notas |
   |---|---|---|---|

   - **Tipo**: el tipo SQL real que crea la migración (`INTEGER`,
     `VARCHAR`, `VARCHAR(32)`, `TIMESTAMP WITH TIME ZONE`), no el tipo Python
     del modelo.
   - **Nulos**: `NO` / `SÍ`.
   - **Notas**: solo cuando el sentido **no** es evidente por el nombre. PK, FK
     (con destino y regla `ON DELETE`), `UNIQUE`, `CHECK` (con su nombre y su
     expresión), valor sembrado por una migración, o el orden en que se añadió
     si no fue en el `CREATE TABLE` original. Si una columna es autoexplicativa
     (`name`, `title`), deja **Notas** vacío.
4. **Constraints y detalles de nivel de base** que no encajan en una fila:
   el nombre del `CHECK`, la constraint `UNIQUE` compuesta si la hay, la
   ausencia de índices sobre las columnas de FK, la tabla `alembic_version`.
5. **Discrepancias** — si algún modelo no coincide con lo que aplican las
   migraciones, una lista con cada una. Si no hay, se omite la sección.

## No repetir el contrato

`docs/contrato-api.md` ya fija: los códigos de estado, los esquemas de
respuesta "ni más ni menos", el orden de las listas, la normalización de
`title`, la serialización de `due_at`, el catálogo de estados y la Matriz
Mínima de Tests. Nada de eso se copia en `docs/esquema.md`.

- Si un dato del esquema está explicado en el contrato, se **enlaza**:
  `ver [§Estados](contrato-api.md#estados)`.
- `docs/esquema.md` añade lo que el contrato **no** dice: nombres y tipos de
  columnas, `position` de `states`, el nombre y la expresión del `CHECK`, las
  reglas `ON DELETE`, `VARCHAR(32)` de `states.code`, la ausencia de índices,
  el orden real de creación de las tablas.
- Si al describir surge algo que contradice el contrato, se anota como
  discrepancia; **no se cambia el contrato** (ver Límite).

## Límite: describe, no modifica

Esta skill **solo** escribe `docs/esquema.md`. Mientras se ejecuta:

- no edita `app/models.py`, ninguna migración de `alembic/versions/`, ni
  ningún otro código, test o configuración;
- no toca los documentos rectores (`docs/contrato-api.md`,
  `docs/decisiones-ingenieria.md`, `CLAUDE.md`, `README.md`);
- no ejecuta migraciones ni ninguna operación contra la base de datos —
  `alembic upgrade`, `psql`, `docker compose` quedan fuera;
- no crea la revisión de Alembic que "faltaría" ni propone cambios de esquema.

Si los modelos y las migraciones discrepan, la skill lo **documenta** en la
sección Discrepancias y sigue; no arregla ninguno de los dos.
