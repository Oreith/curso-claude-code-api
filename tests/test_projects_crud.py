"""CRUD de `/projects` end-to-end contra el PostgreSQL real de Compose.

Cubre los Incrementos 3 y 4: `POST`, `GET` de colección, `GET /{id}` y `PATCH`.
El borrado (`DELETE`) vive en `tests/test_projects_delete.py`.

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
    """Aplica las migraciones una vez para el módulo; las revierte al final."""
    cfg = Config(str(_REPO_ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")


@pytest.fixture(autouse=True)
def tablas_limpias(migrada, engine):
    """Deja `projects` y `tasks` vacías y con los contadores a cero por test."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE tasks, projects RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def client(migrada):
    with TestClient(app) as c:
        yield c


def _crear(client, name="Casa", **extra):
    return client.post("/projects", json={"name": name, **extra})


# --- Incremento 3: POST y GET de colección ------------------------------------


def test_post_crea_201_y_esquema_exacto(client):
    resp = _crear(client, "Casa")
    assert resp.status_code == 201
    cuerpo = resp.json()
    assert set(cuerpo) == {"id", "name", "description"}
    assert cuerpo["name"] == "Casa"
    assert cuerpo["description"] is None
    assert isinstance(cuerpo["id"], int)


def test_post_con_description_se_guarda(client):
    resp = _crear(client, "Casa", description="con jardín")
    assert resp.status_code == 201
    assert resp.json()["description"] == "con jardín"


def test_post_recorta_el_name(client):
    assert _crear(client, "  Casa  ").json()["name"] == "Casa"


def test_post_sin_name_es_422(client):
    resp = client.post("/projects", json={})
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_post_name_en_blanco_es_422(client):
    resp = _crear(client, "   ")
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_post_campo_desconocido_es_422(client):
    resp = client.post("/projects", json={"name": "Casa", "state_id": 1})
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_get_lista_en_la_raiz_y_ordenada_por_id(client):
    for nombre in ("Casa", "Trabajo", "Ocio"):
        assert _crear(client, nombre).status_code == 201

    primera = client.get("/projects")
    assert primera.status_code == 200
    cuerpo = primera.json()
    assert isinstance(cuerpo, list)
    ids = [p["id"] for p in cuerpo]
    assert ids == sorted(ids)
    assert [p["name"] for p in cuerpo] == ["Casa", "Trabajo", "Ocio"]

    # Estable entre dos llamadas idénticas.
    assert client.get("/projects").json() == cuerpo


def test_get_lista_vacia_es_lista(client):
    resp = client.get("/projects")
    assert resp.status_code == 200
    assert resp.json() == []


# --- Incremento 4: GET /{id} y PATCH /{id} -----------------------------------


def test_get_por_id_200_y_esquema_exacto(client):
    creado = _crear(client, "Casa").json()
    resp = client.get(f"/projects/{creado['id']}")
    assert resp.status_code == 200
    assert resp.json() == creado
    assert set(resp.json()) == {"id", "name", "description"}


def test_get_por_id_inexistente_404(client):
    resp = client.get("/projects/999")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_get_por_id_no_entero_422(client):
    resp = client.get("/projects/abc")
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_patch_cambia_solo_lo_enviado(client):
    creado = _crear(client, "Casa").json()
    resp = client.patch(
        f"/projects/{creado['id']}", json={"description": "con jardín"}
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["name"] == "Casa"
    assert cuerpo["description"] == "con jardín"


def test_patch_description_a_null(client):
    creado = _crear(client, "Casa", description="con jardín").json()
    resp = client.patch(f"/projects/{creado['id']}", json={"description": None})
    assert resp.status_code == 200
    assert resp.json()["description"] is None


def test_patch_cuerpo_vacio_200_sin_cambios(client):
    creado = _crear(client, "Casa", description="con jardín").json()
    resp = client.patch(f"/projects/{creado['id']}", json={})
    assert resp.status_code == 200
    assert resp.json() == creado


def test_patch_name_recortado(client):
    creado = _crear(client, "Casa").json()
    resp = client.patch(f"/projects/{creado['id']}", json={"name": "  Hogar "})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Hogar"


def test_patch_name_en_blanco_422(client):
    creado = _crear(client, "Casa").json()
    resp = client.patch(f"/projects/{creado['id']}", json={"name": "   "})
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_patch_id_inexistente_404(client):
    resp = client.patch("/projects/999", json={"name": "Casa"})
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_patch_campo_desconocido_422(client):
    creado = _crear(client, "Casa").json()
    resp = client.patch(f"/projects/{creado['id']}", json={"state_id": 1})
    assert resp.status_code == 422
    assert "detail" in resp.json()
