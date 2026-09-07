"""CRUD de `/tasks` end-to-end contra el PostgreSQL real de Compose.

Cubre los Incrementos 2 y 4 del plan de tareas: `POST`, `GET /{id}`, `PATCH` y
`DELETE`. El listado con filtros vive en `tests/test_tasks_list.py`.

Requiere el servicio `db` de `compose.yaml` levantado y sano.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.config import build_database_url
from app.main import app

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(build_database_url(), future=True)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        eng.dispose()
        pytest.skip(f"PostgreSQL de Compose no disponible: {exc}")
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def migrada(engine):
    cfg = Config(str(_REPO_ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")


@pytest.fixture(autouse=True)
def tablas_limpias(migrada, engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE tasks, projects RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def client(migrada):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def proyecto_id(client) -> int:
    return client.post("/projects", json={"name": "Casa"}).json()["id"]


@pytest.fixture
def estado_id(client) -> int:
    return client.get("/states").json()[0]["id"]


@pytest.fixture
def otro_estado_id(client) -> int:
    return client.get("/states").json()[1]["id"]


def _crear(client, proyecto_id, estado_id, title="Regar", **extra):
    cuerpo = {"title": title, "project_id": proyecto_id, "state_id": estado_id}
    cuerpo.update(extra)
    return client.post("/tasks", json=cuerpo)


# --- Incremento 2: POST y GET /{id} -----------------------------------------

_ESQUEMA_V1 = {"id", "title", "description", "project_id", "state_id"}


def test_post_crea_201_y_esquema_v1_exacto(client, proyecto_id, estado_id):
    resp = _crear(client, proyecto_id, estado_id)
    assert resp.status_code == 201
    cuerpo = resp.json()
    assert set(cuerpo) == _ESQUEMA_V1
    assert cuerpo["title"] == "Regar"
    assert cuerpo["description"] is None
    assert cuerpo["project_id"] == proyecto_id
    assert cuerpo["state_id"] == estado_id


def test_post_con_description(client, proyecto_id, estado_id):
    resp = _crear(client, proyecto_id, estado_id, description="con la manguera")
    assert resp.status_code == 201
    assert resp.json()["description"] == "con la manguera"


def test_post_recorta_el_title(client, proyecto_id, estado_id):
    creada = _crear(client, proyecto_id, estado_id, title="  Regar  ").json()
    assert creada["title"] == "Regar"


@pytest.mark.parametrize("title", ["", "   ", "​", "  "])
def test_post_title_sin_visible_422(client, proyecto_id, estado_id, title):
    resp = _crear(client, proyecto_id, estado_id, title=title)
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_post_project_id_inexistente_422(client, estado_id):
    resp = client.post(
        "/tasks", json={"title": "x", "project_id": 9999, "state_id": estado_id}
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_post_state_id_inexistente_422(client, proyecto_id):
    resp = client.post(
        "/tasks", json={"title": "x", "project_id": proyecto_id, "state_id": 9999}
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_post_campo_desconocido_422(client, proyecto_id, estado_id):
    resp = _crear(client, proyecto_id, estado_id, due_at="2026-03-01T09:00:00Z")
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_post_falta_campo_obligatorio_422(client, proyecto_id):
    resp = client.post("/tasks", json={"title": "x", "project_id": proyecto_id})
    assert resp.status_code == 422


def test_get_por_id_200_esquema_v1_exacto(client, proyecto_id, estado_id):
    creada = _crear(client, proyecto_id, estado_id).json()
    resp = client.get(f"/tasks/{creada['id']}")
    assert resp.status_code == 200
    assert resp.json() == creada
    assert set(resp.json()) == _ESQUEMA_V1


def test_get_por_id_inexistente_404(client):
    resp = client.get("/tasks/9999")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_get_por_id_no_entero_422(client):
    resp = client.get("/tasks/abc")
    assert resp.status_code == 422


# --- Incremento 4: PATCH y DELETE ------------------------------------------


def test_patch_cambia_solo_lo_enviado(client, proyecto_id, estado_id, otro_estado_id):
    creada = _crear(client, proyecto_id, estado_id).json()
    resp = client.patch(f"/tasks/{creada['id']}", json={"state_id": otro_estado_id})
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["state_id"] == otro_estado_id
    assert cuerpo["title"] == creada["title"]
    assert cuerpo["project_id"] == creada["project_id"]


def test_patch_cuerpo_vacio_200_sin_cambios(client, proyecto_id, estado_id):
    creada = _crear(client, proyecto_id, estado_id, description="x").json()
    resp = client.patch(f"/tasks/{creada['id']}", json={})
    assert resp.status_code == 200
    assert resp.json() == creada


def test_patch_description_a_null(client, proyecto_id, estado_id):
    creada = _crear(client, proyecto_id, estado_id, description="x").json()
    resp = client.patch(f"/tasks/{creada['id']}", json={"description": None})
    assert resp.status_code == 200
    assert resp.json()["description"] is None


def test_patch_title_recortado(client, proyecto_id, estado_id):
    creada = _crear(client, proyecto_id, estado_id).json()
    resp = client.patch(f"/tasks/{creada['id']}", json={"title": "  Podar  "})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Podar"


def test_patch_title_sin_visible_422(client, proyecto_id, estado_id):
    creada = _crear(client, proyecto_id, estado_id).json()
    resp = client.patch(f"/tasks/{creada['id']}", json={"title": "​"})
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_patch_project_id_inexistente_422(client, proyecto_id, estado_id):
    creada = _crear(client, proyecto_id, estado_id).json()
    resp = client.patch(f"/tasks/{creada['id']}", json={"project_id": 9999})
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_patch_state_id_inexistente_422(client, proyecto_id, estado_id):
    creada = _crear(client, proyecto_id, estado_id).json()
    resp = client.patch(f"/tasks/{creada['id']}", json={"state_id": 9999})
    assert resp.status_code == 422


def test_patch_id_inexistente_404(client):
    resp = client.patch("/tasks/9999", json={"title": "x"})
    assert resp.status_code == 404


def test_patch_campo_desconocido_422(client, proyecto_id, estado_id):
    creada = _crear(client, proyecto_id, estado_id).json()
    tid = creada["id"]
    resp = client.patch(f"/tasks/{tid}", json={"due_at": "2026-03-01T09:00:00Z"})
    assert resp.status_code == 422


def test_delete_204_sin_cuerpo(client, proyecto_id, estado_id):
    creada = _crear(client, proyecto_id, estado_id).json()
    resp = client.delete(f"/tasks/{creada['id']}")
    assert resp.status_code == 204
    assert resp.content == b""
    assert client.get(f"/tasks/{creada['id']}").status_code == 404


def test_delete_id_inexistente_404(client):
    resp = client.delete("/tasks/9999")
    assert resp.status_code == 404


def test_delete_ultima_tarea_permite_borrar_el_proyecto(client, proyecto_id, estado_id):
    creada = _crear(client, proyecto_id, estado_id).json()
    assert client.delete(f"/projects/{proyecto_id}").status_code == 409
    client.delete(f"/tasks/{creada['id']}")
    assert client.delete(f"/projects/{proyecto_id}").status_code == 204


def test_borrar_proyecto_con_tarea_creada_por_api_responde_409(client, estado_id):
    """Todo el flujo por la API: crear proyecto, crear tarea sobre él, borrar el
    proyecto -> 409 (docs/contrato-api.md §Proyectos, sin cascada implícita)."""
    proyecto_id = client.post("/projects", json={"name": "Casa"}).json()["id"]
    tarea = client.post(
        "/tasks",
        json={"title": "Regar", "project_id": proyecto_id, "state_id": estado_id},
    )
    assert tarea.status_code == 201

    resp = client.delete(f"/projects/{proyecto_id}")
    assert resp.status_code == 409
    assert "detail" in resp.json()

    # El proyecto y la tarea siguen ahí: no hubo borrado en cascada.
    assert client.get(f"/projects/{proyecto_id}").status_code == 200
    assert client.get(f"/tasks/{tarea.json()['id']}").status_code == 200
