"""`GET /tasks?overdue=true` (Tareas v2).

Contrato §Tareas v2: devuelve las tareas con `due_at` anterior al instante de
evaluación y estado distinto de `HECHA`. Una tarea sin fecha no está vencida.
Combinable con `project_id` y `state_id`; orden por `id`.

Requiere el servicio `db` de `compose.yaml` levantado y sano.
"""

from datetime import UTC, datetime, timedelta
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
def estados(client) -> dict[str, int]:
    return {s["code"]: s["id"] for s in client.get("/states").json()}


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


_PASADO = _iso(datetime.now(UTC) - timedelta(days=1))
_FUTURO = _iso(datetime.now(UTC) + timedelta(days=1))


def _proyecto(client, nombre: str = "Casa") -> int:
    return client.post("/projects", json={"name": nombre}).json()["id"]


def _tarea(client, project_id: int, state_id: int, due_at: str | None) -> int:
    return client.post(
        "/tasks",
        json={
            "title": "t",
            "project_id": project_id,
            "state_id": state_id,
            "due_at": due_at,
        },
    ).json()["id"]


def test_vencida_aparece(client, estados):
    p = _proyecto(client)
    tid = _tarea(client, p, estados["PENDIENTE"], _PASADO)
    cuerpo = client.get("/tasks?overdue=true").json()
    assert [t["id"] for t in cuerpo] == [tid]


def test_futura_no_aparece(client, estados):
    p = _proyecto(client)
    _tarea(client, p, estados["PENDIENTE"], _FUTURO)
    assert client.get("/tasks?overdue=true").json() == []


def test_sin_due_at_no_aparece(client, estados):
    p = _proyecto(client)
    _tarea(client, p, estados["PENDIENTE"], None)
    assert client.get("/tasks?overdue=true").json() == []


def test_vencida_pero_hecha_no_aparece(client, estados):
    p = _proyecto(client)
    _tarea(client, p, estados["HECHA"], _PASADO)
    assert client.get("/tasks?overdue=true").json() == []


def test_overdue_combinado_con_project_id(client, estados):
    p1, p2 = _proyecto(client, "Casa"), _proyecto(client, "Trabajo")
    esperada = _tarea(client, p1, estados["PENDIENTE"], _PASADO)
    _tarea(client, p2, estados["PENDIENTE"], _PASADO)

    cuerpo = client.get(f"/tasks?overdue=true&project_id={p1}").json()
    assert [t["id"] for t in cuerpo] == [esperada]


def test_overdue_orden_por_id_estable(client, estados):
    p = _proyecto(client)
    ids = [_tarea(client, p, estados["EN_CURSO"], _PASADO) for _ in range(3)]
    primera = client.get("/tasks?overdue=true").json()
    assert [t["id"] for t in primera] == sorted(ids)
    assert client.get("/tasks?overdue=true").json() == primera


def test_overdue_false_no_filtra(client, estados):
    p = _proyecto(client)
    _tarea(client, p, estados["PENDIENTE"], _FUTURO)
    _tarea(client, p, estados["PENDIENTE"], None)
    assert len(client.get("/tasks?overdue=false").json()) == 2
    assert len(client.get("/tasks").json()) == 2
