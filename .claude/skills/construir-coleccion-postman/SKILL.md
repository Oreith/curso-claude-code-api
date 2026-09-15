---
name: construir-coleccion-postman
description: >-
  Construye o actualiza en Postman la colección de este proyecto a partir de
  openapi.json: una petición por operación, con método, ruta, cuerpo de
  ejemplo, resumen, descripción y una comprobación del código de estado del
  caso correcto. Busca el espacio de trabajo del proyecto y lo crea solo si
  no existe, y hace lo mismo con el environment y sus variables. Lee
  openapi.json y escribe en Postman; no toca código ni especificación.
allowed-tools: >-
  Read, mcp__postman__getWorkspaces, mcp__postman__createWorkspace,
  mcp__postman__getCollections, mcp__postman__createCollection,
  mcp__postman__putCollection, mcp__postman__getEnvironments,
  mcp__postman__createEnvironment, mcp__postman__putEnvironment
---

# construir-coleccion-postman

Construye o actualiza, en el espacio de trabajo de Postman de este proyecto,
una colección con una petición por operación de `openapi.json`. No modifica
`openapi.json` ni el código de la API.

## Punto de partida: `openapi.json`, no el código

Lee `openapi.json` con `Read`. Es la única fuente para las peticiones: no
regeneres la especificación ni leas `app/routers/` o `app/schemas.py` para
completar campos — si algo falta en `openapi.json`, falta también en la
petición de Postman. (Comprobar que `openapi.json` está al día es otra tarea,
ya cubierta por el hook `openapi-al-dia.sh`; esta skill no lo verifica ni lo
regenera.)

De `openapi.json` toma:

- **`info.title`**: para nombrar la colección.
- Por cada combinación ruta+método en `paths`: `summary`, `description` (si
  falta, cadena vacía — no la inventes), `operationId`, `requestBody` y
  `responses`.

## Nombre del espacio de trabajo: derivado, estable

El nombre del workspace es el nombre del repositorio: el último segmento de
`git remote get-url origin` (o del directorio del repo si no hay remoto), sin
`.git` ni la organización. Para este repositorio es `curso-claude-code-api`.
Ese nombre es estable entre invocaciones: no le añadas fecha, sufijo ni hash.
El environment del paso 5 usa el mismo nombre, para que quede claro a qué
proyecto pertenece.

## Orden

1. **Busca el workspace.** `mcp__postman__getWorkspaces` y filtra por el
   nombre derivado. Si existe, usa su `id`. **Si no existe, créalo** con
   `mcp__postman__createWorkspace` (`type: "personal"`) — una sola vez; no
   crees uno nuevo si ya apareció en la búsqueda, aunque su tipo o
   visibilidad no sea el que tú hubieras elegido.
2. **Busca la colección.** `mcp__postman__getCollections` con ese
   `workspace` y `name` igual al `info.title` de `openapi.json`. Como el
   filtro por nombre es exacto, un resultado significa que ya existe: guarda
   su `id`.
3. **Arma el árbol de peticiones** (ver abajo), una por cada operación de
   `openapi.json`.
4. **Crea o actualiza la colección completa:**
   - Si no existía (paso 2 sin resultados): `mcp__postman__createCollection`
     con el árbol armado, en ese `workspace`.
   - Si ya existía: `mcp__postman__putCollection` con ese `collectionId`,
     reemplazando el contenido completo por el árbol armado. `putCollection`
     sustituye todos los `item`; por eso el árbol de este mismo paso ya debe
     traer **todas** las operaciones vigentes de `openapi.json`, no solo las
     que cambiaron.
5. **Busca o crea el environment y asegura sus variables** (ver
   "Environment y variables" abajo).
6. Informa el resultado (ver "Qué contar al final").

## Una petición por operación

Para cada ruta y método de `paths` en `openapi.json`:

- **Nombre de la petición**: el `summary` de la operación. Si no trae
  `summary`, usa `operationId`; si tampoco lo trae, `"<MÉTODO> <ruta>"`.
- **Método y URL**: el método HTTP de la clave y la ruta tal cual aparece en
  `openapi.json`, con `{param}` como variable de ruta de Postman (mismo
  nombre, sin llaves en el segmento — formato `:param` o el que use la
  versión del schema de colección que estés emitiendo).
- **Resumen y descripción**: copia literal de `summary` y `description` de la
  operación al campo `description` de la petición (Postman no separa ambos:
  concaténalos, `summary` primero, en negrita o como primera línea, seguido
  de `description` si la hay). Estos campos se **vuelven a copiar** cada vez
  que la skill corre — si cambiaron en `openapi.json`, la nueva ejecución los
  actualiza porque `putCollection` reemplaza el árbol completo.
- **Cuerpo de ejemplo**: cuando la operación declara `requestBody` con
  contenido `application/json`, resuelve su `schema` (siguiendo `$ref` contra
  `components/schemas`) y arma un objeto JSON de ejemplo:
  - usa el `example` o `default` del esquema o de cada propiedad si los trae;
  - si no, un valor plausible por tipo (`""` para `string`, `0` para
    `integer`/`number`, `false` para `boolean`, `[]`/`{}` para `array`/
    `object`) respetando `enum` (toma el primer valor) y campos `required`.
  - Operaciones sin `requestBody` (los `GET`, los `DELETE` de este proyecto)
    no llevan cuerpo.
- **Comprobación del caso correcto**: un test script (`event` tipo `test`)
  que compruebe el código de estado 2xx que declara `responses` para esa
  operación — en este proyecto, `200` o `201` según el método. Si
  `responses` declara más de un código 2xx, usa el más bajo. Ejemplo de
  script (ajusta el código):

  ```javascript
  pm.test("El caso correcto responde 201", function () {
      pm.response.to.have.status(201);
  });
  ```

  No generes comprobaciones para los códigos de error (`404`, `422`): el
  contrato ya los fija en `docs/contrato-api.md` y esta skill no es la
  encargada de probarlos.

## Environment y variables

Las peticiones usan `{{baseUrl}}` y variables de ruta (`:project_id`,
`:state_id`, `:task_id`). El environment les da valor.

1. **Busca el environment.** `mcp__postman__getEnvironments` con ese
   `workspace` y compara por nombre exacto contra el nombre derivado del
   repositorio (el mismo del workspace). Si no aparece, créalo con
   `mcp__postman__createEnvironment`.
2. **Variables que debe tener, como mínimo:**
   - `baseUrl` — la URL del servidor local que documenta `README.md`
     (`http://127.0.0.1:8000` en este repositorio). No la inventes: tómala de
     ahí, y si `README.md` cambia esa URL en el futuro, actualízala aquí
     también.
   - una variable de prueba por cada nombre de parámetro de ruta que aparezca
     en `paths` de `openapi.json` (aquí: `project_id`, `state_id`,
     `task_id`), con un valor de ejemplo simple (`1`) para que las peticiones
     con path params sean ejecutables sin editarlas a mano.
3. **No pises valores que ya estén.** Si el environment ya existía, léelo
   primero (el resultado de `getEnvironments` o, si hace falta el detalle
   completo, `mcp__postman__getEnvironment`) y arma la lista de `values` para
   `mcp__postman__putEnvironment` **fusionando**: conserva tal cual cada
   variable existente que no sea una de las que gestiona esta skill (`baseUrl`
   y las variables de path params derivadas de `openapi.json`), y solo crea o
   sobrescribe esas. `putEnvironment` reemplaza el array completo de
   `values`, así que una variable que falte en la lista que envías
   desaparece del environment.
4. Si el environment no existía, créalo directamente con `baseUrl` y las
   variables de path params — no hay nada que fusionar.

## Qué contar al final

Termina el mensaje al usuario con:

- si el workspace se **creó** o ya **existía** (con su nombre);
- si la colección se **creó** o se **actualizó** (con su nombre);
- el número de peticiones que quedaron en la colección tras esta ejecución,
  y — solo si la colección ya existía — cuántas de esas peticiones son
  nuevas respecto a las operaciones que había antes (comparando por método +
  ruta contra lo que devolvió `getCollections`/la colección previa) frente a
  cuántas ya existían y solo se refrescaron;
- si el environment se **creó** o ya **existía** (con su nombre), y qué
  variables quedaron gestionadas por la skill (`baseUrl` y cada variable de
  path param).

## Límite

Esta skill solo lee `openapi.json` y escribe en Postman. Mientras corre:

- no edita `openapi.json`, ni ningún archivo de `app/`, ni ninguna migración;
- no ejecuta `uv run python -c ...` para regenerar la especificación — si
  sospechas que `openapi.json` está desactualizado, dilo en el resultado
  final y sugiere comprobarlo, pero no lo regeneres tú;
- no crea un segundo workspace, una segunda colección ni un segundo
  environment para el mismo proyecto si ya encontró uno por nombre, aunque no
  sea exactamente como tú lo habrías creado;
- no borra ni sobrescribe variables del environment que no gestione ella
  (`baseUrl` y las variables de path params derivadas de `openapi.json`);
- no toca mocks, specs de Postman ni ningún otro elemento de Postman fuera de
  la colección y el environment.
