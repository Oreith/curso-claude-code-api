"""`due_at` en entrada y salida de `/tasks` (Tareas v2).

Contrato §Tareas v2 y §Esquemas de Respuesta: `due_at` opcional, con zona
horaria, normalizado a UTC; se serializa siempre en UTC con sufijo `Z` y sin
microsegundos; omitirlo conserva la compatibilidad v1; una fecha sin zona se
rechaza con `422`.

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
_ESQUEMA_TAREA = {"id", "title", "description", "project_id", "state_id", "due_at"}


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


def test_post_sin_due_at_devuelve_null(client, proyecto_id, estado_id):
    cuerpo = _crear(client, proyecto_id, estado_id).json()
    assert set(cuerpo) == _ESQUEMA_TAREA
    assert cuerpo["due_at"] is None


def test_post_due_at_con_offset_se_normaliza_a_z(client, proyecto_id, estado_id):
    cuerpo = _crear(
        client, proyecto_id, estado_id, due_at="2026-03-01T11:00:00+02:00"
    ).json()
    assert cuerpo["due_at"] == "2026-03-01T09:00:00Z"


def test_post_due_at_con_z(client, proyecto_id, estado_id):
    cuerpo = _crear(
        client, proyecto_id, estado_id, due_at="2026-03-01T09:00:00Z"
    ).json()
    assert cuerpo["due_at"] == "2026-03-01T09:00:00Z"


def test_post_due_at_con_microsegundos_se_trunca(client, proyecto_id, estado_id):
    cuerpo = _crear(
        client, proyecto_id, estado_id, due_at="2026-03-01T09:00:00.123456Z"
    ).json()
    assert cuerpo["due_at"] == "2026-03-01T09:00:00Z"


def test_post_due_at_sin_zona_422(client, proyecto_id, estado_id):
    resp = _crear(client, proyecto_id, estado_id, due_at="2026-03-01T09:00:00")
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_post_due_at_null_explicito(client, proyecto_id, estado_id):
    cuerpo = _crear(client, proyecto_id, estado_id, due_at=None).json()
    assert cuerpo["due_at"] is None


def test_patch_due_at_pone_y_quita(client, proyecto_id, estado_id):
    tid = _crear(client, proyecto_id, estado_id).json()["id"]

    puesta = client.patch(
        f"/tasks/{tid}", json={"due_at": "2026-03-01T09:00:00Z"}
    ).json()
    assert puesta["due_at"] == "2026-03-01T09:00:00Z"

    quitada = client.patch(f"/tasks/{tid}", json={"due_at": None}).json()
    assert quitada["due_at"] is None


def test_patch_due_at_sin_zona_422(client, proyecto_id, estado_id):
    tid = _crear(client, proyecto_id, estado_id).json()["id"]
    resp = client.patch(f"/tasks/{tid}", json={"due_at": "2026-03-01T09:00:00"})
    assert resp.status_code == 422


def test_get_por_id_incluye_due_at(client, proyecto_id, estado_id):
    creada = _crear(
        client, proyecto_id, estado_id, due_at="2026-03-01T09:00:00Z"
    ).json()
    obtenida = client.get(f"/tasks/{creada['id']}").json()
    assert obtenida == creada
    assert set(obtenida) == _ESQUEMA_TAREA
