"""`GET /tasks` con filtros `project_id` y `state_id` (Incremento 3).

Contrato §Tareas v1 y §Orden de las listas: lista JSON en la raíz, orden por
`id` ascendente también con filtros, `project_id` y `state_id` solos o
combinados.

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
_ESQUEMA_V1 = {"id", "title", "description", "project_id", "state_id"}


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
def estados(client) -> list[int]:
    return [s["id"] for s in client.get("/states").json()]


def _proyecto(client, nombre: str) -> int:
    return client.post("/projects", json={"name": nombre}).json()["id"]


def _tarea(client, project_id: int, state_id: int, title: str = "t") -> int:
    return client.post(
        "/tasks",
        json={"title": title, "project_id": project_id, "state_id": state_id},
    ).json()["id"]


def test_lista_vacia_es_lista(client):
    resp = client.get("/tasks")
    assert resp.status_code == 200
    assert resp.json() == []


def test_orden_por_id_estable_y_esquema(client, estados):
    p = _proyecto(client, "Casa")
    for _ in range(3):
        _tarea(client, p, estados[0])

    primera = client.get("/tasks")
    assert primera.status_code == 200
    cuerpo = primera.json()
    assert isinstance(cuerpo, list)
    ids = [t["id"] for t in cuerpo]
    assert ids == sorted(ids)
    assert all(set(t) == _ESQUEMA_V1 for t in cuerpo)
    assert client.get("/tasks").json() == cuerpo


def test_filtro_project_id(client, estados):
    p1, p2 = _proyecto(client, "Casa"), _proyecto(client, "Trabajo")
    _tarea(client, p1, estados[0])
    _tarea(client, p1, estados[0])
    _tarea(client, p2, estados[0])

    cuerpo = client.get(f"/tasks?project_id={p1}").json()
    assert {t["project_id"] for t in cuerpo} == {p1}
    assert len(cuerpo) == 2


def test_filtro_state_id(client, estados):
    p = _proyecto(client, "Casa")
    _tarea(client, p, estados[0])
    _tarea(client, p, estados[1])
    _tarea(client, p, estados[1])

    cuerpo = client.get(f"/tasks?state_id={estados[1]}").json()
    assert {t["state_id"] for t in cuerpo} == {estados[1]}
    assert len(cuerpo) == 2


def test_filtros_combinados(client, estados):
    p1, p2 = _proyecto(client, "Casa"), _proyecto(client, "Trabajo")
    _tarea(client, p1, estados[0])
    _tarea(client, p1, estados[1])
    _tarea(client, p2, estados[1])

    cuerpo = client.get(f"/tasks?project_id={p1}&state_id={estados[1]}").json()
    assert len(cuerpo) == 1
    assert cuerpo[0]["project_id"] == p1
    assert cuerpo[0]["state_id"] == estados[1]


def test_filtro_sin_coincidencias_200_lista_vacia(client, estados):
    p = _proyecto(client, "Casa")
    _tarea(client, p, estados[0])
    resp = client.get("/tasks?project_id=9999")
    assert resp.status_code == 200
    assert resp.json() == []
