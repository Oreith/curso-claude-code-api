"""La especificación OpenAPI declara lo que el contrato exige y el schema puede
expresar (ver la comparación en `docs/contrato-api.md` y `openapi.json`).

Cubre solo lo *declarativo*: los conjuntos cerrados como `enum`, y las
respuestas de error (`404`, `409`) en las operaciones que las producen. Las
invariantes que OpenAPI no puede expresar (orden estable, idempotencia del
seed, formato exacto de `due_at`, semántica de `overdue`) quedan fuera.

`app.openapi()` es una función pura: no abre conexión ni necesita la base.
"""

import json
from pathlib import Path

from app.main import app

_ESQUEMA = app.openapi()
_SCHEMAS = _ESQUEMA["components"]["schemas"]
_PATHS = _ESQUEMA["paths"]

_PRIORIDADES = ["BAJA", "MEDIA", "ALTA"]
_ESTADOS = ["PENDIENTE", "EN_CURSO", "BLOQUEADA", "HECHA"]


def _enum_de(schema: dict, campo: str) -> list:
    """Devuelve el `enum` de un campo declarado como `Literal | None` (anyOf)."""
    prop = schema["properties"][campo]
    if "enum" in prop:
        return prop["enum"]
    for rama in prop.get("anyOf", []):
        if "enum" in rama:
            return rama["enum"]
    raise AssertionError(f"{campo} no declara enum: {prop}")


def test_version_sigue_la_fase_del_contrato():
    # El contrato va por "Tareas v3"; la spec no puede quedarse en 0.1.0.
    assert _ESQUEMA["info"]["version"] == "0.3.0"


def test_priority_es_conjunto_cerrado_en_los_tres_esquemas():
    for nombre in ("TaskCreate", "TaskUpdate", "TaskOut"):
        assert _enum_de(_SCHEMAS[nombre], "priority") == _PRIORIDADES


def test_state_code_es_el_catalogo_cerrado():
    assert _enum_de(_SCHEMAS["StateOut"], "code") == _ESTADOS


def test_get_por_id_declara_404():
    for ruta in ("/projects/{project_id}", "/tasks/{task_id}"):
        for metodo in ("get", "patch", "delete"):
            respuestas = _PATHS[ruta][metodo]["responses"]
            assert "404" in respuestas, f"{metodo.upper()} {ruta} sin 404"


def test_delete_project_declara_409():
    respuestas = _PATHS["/projects/{project_id}"]["delete"]["responses"]
    assert "409" in respuestas


def test_openapi_json_coincide_con_el_codigo():
    # El hook de sesión (.claude/hooks/openapi-al-dia.sh) bloquea el commit
    # si openapi.json no coincide, pero eso solo protege commits hechos a
    # través de Claude Code. Este test lo protege también en CI y para
    # cualquier otro flujo de commit.
    ruta = Path(__file__).resolve().parent.parent / "openapi.json"
    en_disco = json.loads(ruta.read_text(encoding="utf-8"))
    assert en_disco == _ESQUEMA, (
        "openapi.json no coincide con app.openapi(). Regenéralo con el "
        "comando de README.md §Especificación OpenAPI."
    )
