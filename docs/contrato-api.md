# Contrato de la API del Curso

Este documento fija comportamiento observable. La estructura interna queda
abierta salvo las restricciones de seguridad, migración y verificación.

## Convenciones

- JSON UTF-8 y fechas ISO 8601.
- IDs enteros positivos generados por la base.
- `404` para recurso inexistente, `409` para conflicto y `422` para entrada inválida.
- Los códigos de las tablas siguientes son parte del contrato: son lo que
  afirman los tests, y lo que la sesión 10 compara al revisar. No los cambies
  sin cambiar antes este documento.
- Errores con forma estable: `{"detail": "<mensaje>"}`, donde el mensaje es una
  cadena legible. Para un `422` de validación se admite además la forma que
  genere tu framework, siempre que la clave de primer nivel siga siendo
  `detail`. El valor de `detail` puede entonces ser una lista en lugar de una
  cadena; un consumidor solo debe apoyarse en la presencia de la clave
  `detail`, no en su tipo.
- Una referencia a proyecto o estado inexistente no se crea implícitamente.
- Los campos de texto libre (`name`, `title`, `description`) no tienen longitud
  máxima: ningún valor se rechaza por largo.

### Normalización de texto

Se aplica a `title` de tarea, **antes** de validar y guardar:

1. Se recorta el espacio de los extremos.
2. Se rechaza con `422` el valor que no deja **ningún carácter visible**. No
   basta con `strip()`: hay invisibles —como `U+200B`— que lo atraviesan. La
   comprobación es por categoría Unicode, rechazando `Cc`, `Cf`, `Zl`, `Zp`
   y `Zs`.

La sesión 7 trabaja este defecto a fondo, con un título que parece válido y no
lo es.

### Orden de las listas

Toda colección devuelve un orden **estable entre llamadas idénticas**, para que
un test pueda comparar por posición:

| Endpoint | Orden |
|---|---|
| `GET /states` | Por el campo de orden del catálogo, y `id` como desempate |
| `GET /projects` | Por `id` ascendente |
| `GET /tasks` | Por `id` ascendente, también con filtros aplicados |

## Salud

### `GET /health`

Responde `200`:

```json
{"status": "ok"}
```

No expone credenciales ni detalles internos.

## Estados

Catálogo fijo: `PENDIENTE`, `EN_CURSO`, `BLOQUEADA`, `HECHA`.

**No tiene endpoints.** Los estados no se crean ni se borran desde la API: son un
catálogo cerrado que existe antes de que llegue la primera petición.

| Método y ruta | Comportamiento |
|---|---|
| `GET /states` | `200` con la lista, ordenada por el campo de orden y `id` como desempate |

Lo único que hay que resolver es **cómo llega ese catálogo a la base**, y ahí está
la decisión que importa:

| Dónde vive el seed | Cuándo se ejecuta |
|---|---|
| Script de inicialización de Docker | Solo al crear el volumen por primera vez |
| **Migración** | En cada `upgrade`, en cualquier entorno |

El curso adopta la migración. Con el script de Docker, quien ya tenía el volumen
creado nunca recibe el catálogo: el proyecto funciona en la máquina donde se
creó y falla en la siguiente.

El seed debe ser [idempotente](../docs/glosario.md#idempotente) —ejecutarlo dos
veces deja lo mismo que una—.

## Proyectos

Campos mínimos: `id`, `name`, `description` opcional.

| Método y ruta | Comportamiento |
|---|---|
| `POST /projects` | `201` con el recurso creado |
| `GET /projects` | `200` con orden determinista |
| `GET /projects/{id}` | `200`, o `404` si no existe |
| `PATCH /projects/{id}` | `200` con actualización parcial |
| `DELETE /projects/{id}` | `204` si no tiene tareas, `409` si las tiene |

El curso adopta `409` al intentar borrar un proyecto con tareas; no hay borrado
en cascada implícito.

## Tareas v1

Campos: `id`, `title`, `description` opcional, `project_id`, `state_id`.

| Método y ruta | Comportamiento |
|---|---|
| `POST /tasks` | `201`; valida proyecto, estado y título |
| `GET /tasks` | `200`; admite `project_id` y `state_id`, solos o combinados |
| `GET /tasks/{id}` | `200`, o `404` si no existe |
| `PATCH /tasks/{id}` | `200` con actualización parcial consistente |
| `DELETE /tasks/{id}` | `204` sin cuerpo |

Un filtro que no casa con ninguna fila devuelve `200` con una lista vacía, no
`404`: `404` queda para un recurso ausente en la ruta, no en la query.

## Tareas v2: Fechas Límite

Se añade `due_at`, opcional, con zona horaria y normalizado a UTC. Omitirlo
conserva compatibilidad v1. Una fecha **sin** zona se rechaza con `422`: es
ambigua, y el contrato no supone ninguna por su cuenta.

`GET /tasks?overdue=true` devuelve tareas con `due_at` anterior al instante de
evaluación y estado distinto de `HECHA`. Una tarea sin fecha no está vencida.

El parámetro `overdue` admite **exactamente** `true` y `false`, en minúsculas:
`true` activa el filtro, `false` (o la ausencia del parámetro) lo deja
inactivo, y cualquier otro valor —`TRUE`, `1`, `yes`, una cadena arbitraria—
se rechaza con `422`.

Fuera de alcance: recordatorios, scheduler, zona preferida del usuario y cambio
automático de estado.

## Tareas v3: Prioridad

Se añade `priority`, opcional. Cuando está presente, su valor es uno de `BAJA`,
`MEDIA` o `ALTA` — un conjunto cerrado de literales, no una tabla y sin endpoint
propio. Cualquier otro valor (otra cadena, distinta capitalización, un número)
se rechaza con `422`.

Omitirlo conserva compatibilidad con v1 y v2: una tarea sin prioridad se
devuelve con `priority` en `null`, no se omite. `PATCH` puede fijarla,
cambiarla o volverla a `null` explícitamente.

`priority` no altera el orden de `GET /tasks`, que sigue siendo por `id`.

## Esquemas de Respuesta

Estos son los campos que devuelve cada recurso. **Ni más ni menos**: un campo de
sobra rompe a quien consuma la API igual que uno que falta.

```json
// Estado
{"id": 1, "code": "PENDIENTE"}

// Proyecto
{"id": 1, "name": "Casa", "description": null}

// Tarea (v3; en v2 sin priority, en v1 además sin due_at)
{
  "id": 1,
  "title": "Regar las plantas",
  "description": null,
  "project_id": 1,
  "state_id": 1,
  "due_at": "2026-03-01T09:00:00Z",
  "priority": null
}
```

Tres detalles que deciden si dos implementaciones son intercambiables:

- Un campo opcional ausente se devuelve como `null`, no se omite.
- `due_at` se serializa **siempre en UTC y con `Z`**, no con desplazamiento
  (`+00:00`), y sin microsegundos: `2026-03-01T09:00:00Z`.
- `GET` de colección devuelve una lista JSON en la raíz, no un objeto envolvente
  con metadatos.

## Matriz Mínima de Tests

- Salud.
- CRUD feliz de proyectos y de tareas.
- IDs inexistentes.
- Título vacío y espacios ASCII; los invisibles Unicode se trabajan como regresión en la sesión 7.
- Proyecto o estado inexistente al crear una tarea.
- Borrado de proyecto con tareas (`409`).
- Filtros solos y combinados.
- Orden estable: dos llamadas idénticas devuelven los ids en la misma posición.
- Esquema de respuesta exacto: los campos declarados, ni uno más.
- Migración desde base vacía y rollback de v2 y de v3.
- El catálogo de estados existe tras migrar, y migrar dos veces no lo duplica.
- `due_at` omitido, válido, sin zona, vencido, futuro y tarea hecha.
- `overdue` acepta solo `true`/`false` en minúsculas; cualquier otro valor es `422`.
- `priority` omitido, con cada valor válido y con valor inválido.

Los tests pueden incluir casos adicionales. No pueden debilitar estas invariantes.
