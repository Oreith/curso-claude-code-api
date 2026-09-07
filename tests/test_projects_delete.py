"""`DELETE /projects/{id}` contra el PostgreSQL real de Compose (Incremento 5).

- `204` sin cuerpo si el proyecto no tiene tareas;
- `404` si el proyecto no existe;
- `409` si tiene tareas, sin borrar el proyecto ni sus tareas (sin cascada).

Como no hay endpoint de tareas, las filas de `tasks` se insertan por SQL directo
con un `state_id` del catálogo ya sembrado por la migración.

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


def _añade_tarea(engine, project_id: int) -> None:
    with engine.begin() as conn:
        state_id = conn.execute(text("SELECT id FROM states LIMIT 1")).scalar_one()
        conn.execute(
            text(
                "INSERT INTO tasks (title, project_id, state_id) "
                "VALUES (:t, :p, :s)"
            ),
            {"t": "Regar", "p": project_id, "s": state_id},
        )


def _cuenta_tareas(engine, project_id: int) -> int:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT count(*) FROM tasks WHERE project_id = :p"),
            {"p": project_id},
        ).scalar_one()


def test_delete_sin_tareas_204_sin_cuerpo(client):
    creado = client.post("/projects", json={"name": "Casa"}).json()
    resp = client.delete(f"/projects/{creado['id']}")
    assert resp.status_code == 204
    assert resp.content == b""
    assert client.get(f"/projects/{creado['id']}").status_code == 404


def test_delete_id_inexistente_404(client):
    resp = client.delete("/projects/999")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_delete_con_tareas_409(client, engine):
    creado = client.post("/projects", json={"name": "Casa"}).json()
    _añade_tarea(engine, creado["id"])

    resp = client.delete(f"/projects/{creado['id']}")
    assert resp.status_code == 409
    assert "detail" in resp.json()


def test_delete_con_tareas_no_borra_el_proyecto(client, engine):
    creado = client.post("/projects", json={"name": "Casa"}).json()
    _añade_tarea(engine, creado["id"])

    client.delete(f"/projects/{creado['id']}")

    assert client.get(f"/projects/{creado['id']}").status_code == 200


def test_delete_con_tareas_no_borra_las_tareas(client, engine):
    creado = client.post("/projects", json={"name": "Casa"}).json()
    _añade_tarea(engine, creado["id"])

    client.delete(f"/projects/{creado['id']}")

    assert _cuenta_tareas(engine, creado["id"]) == 1
