"""`priority` en `/tasks` (Tareas v3).

Contrato §Tareas v3: campo opcional; su valor, si está presente, es uno de
`BAJA`, `MEDIA` o `ALTA`; cualquier otro valor se rechaza con `422`; omitirlo
lo devuelve como `null`; `PATCH` puede fijarlo, cambiarlo o volverlo a `null`.

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
_ESQUEMA_TAREA = {
    "id",
    "title",
    "description",
    "project_id",
    "state_id",
    "due_at",
    "priority",
}


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


def _crear(client, proyecto_id, estado_id, **extra):
    cuerpo = {"title": "Regar", "project_id": proyecto_id, "state_id": estado_id}
    cuerpo.update(extra)
    return client.post("/tasks", json=cuerpo)


def test_post_sin_priority_devuelve_null(client, proyecto_id, estado_id):
    cuerpo = _crear(client, proyecto_id, estado_id).json()
    assert set(cuerpo) == _ESQUEMA_TAREA
    assert cuerpo["priority"] is None


@pytest.mark.parametrize("valor", ["BAJA", "MEDIA", "ALTA"])
def test_post_priority_valida(client, proyecto_id, estado_id, valor):
    resp = _crear(client, proyecto_id, estado_id, priority=valor)
    assert resp.status_code == 201
    assert resp.json()["priority"] == valor


@pytest.mark.parametrize("valor", ["URGENTE", "alta", "baja", "", "1", 3])
def test_post_priority_invalida_422(client, proyecto_id, estado_id, valor):
    resp = _crear(client, proyecto_id, estado_id, priority=valor)
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_post_priority_null_explicito(client, proyecto_id, estado_id):
    creada = _crear(client, proyecto_id, estado_id, priority=None).json()
    assert creada["priority"] is None


def test_patch_priority_pone_cambia_y_quita(client, proyecto_id, estado_id):
    tid = _crear(client, proyecto_id, estado_id).json()["id"]

    def patch(valor):
        r = client.patch(f"/tasks/{tid}", json={"priority": valor})
        return r.json()["priority"]

    assert patch("ALTA") == "ALTA"
    assert patch("BAJA") == "BAJA"
    assert patch(None) is None


def test_patch_priority_invalida_422(client, proyecto_id, estado_id):
    tid = _crear(client, proyecto_id, estado_id).json()["id"]
    resp = client.patch(f"/tasks/{tid}", json={"priority": "media"})
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_priority_no_altera_el_orden(client, proyecto_id, estado_id):
    a = _crear(client, proyecto_id, estado_id, priority="BAJA").json()["id"]
    b = _crear(client, proyecto_id, estado_id, priority="ALTA").json()["id"]
    c = _crear(client, proyecto_id, estado_id).json()["id"]
    ids = [t["id"] for t in client.get("/tasks").json()]
    assert ids == sorted([a, b, c])


def test_get_por_id_incluye_priority(client, proyecto_id, estado_id):
    creada = _crear(client, proyecto_id, estado_id, priority="MEDIA").json()
    obtenida = client.get(f"/tasks/{creada['id']}").json()
    assert obtenida == creada
    assert set(obtenida) == _ESQUEMA_TAREA
