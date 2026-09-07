"""Migración de la tabla `tasks` (solo esquema), contra el PostgreSQL de Compose.

Comprobación del Incremento 2:

- tras `upgrade head`, `tasks` tiene exactamente `id`, `title`, `description`,
  `project_id` y `state_id` (sin `due_at`), con la nulabilidad correcta;
- hay una FK `project_id -> projects.id` y otra `state_id -> states.id`, ambas
  con regla de borrado `RESTRICT`;
- `downgrade` elimina `tasks` sin tocar `projects` ni `states`.

Requiere el servicio `db` de `compose.yaml` levantado y sano.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import build_database_url

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
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


@pytest.fixture
def alembic_config() -> Config:
    return Config(str(_REPO_ROOT / "alembic.ini"))


def _reset_base(engine, alembic_config) -> None:
    command.downgrade(alembic_config, "base")
    with engine.begin() as conn:
        for tabla in inspect(conn).get_table_names():
            conn.execute(text(f'DROP TABLE IF EXISTS "{tabla}" CASCADE'))


@pytest.fixture(autouse=True)
def base_limpia(engine, alembic_config):
    _reset_base(engine, alembic_config)
    yield
    _reset_base(engine, alembic_config)


def test_columnas_de_tasks_sin_due_at(engine, alembic_config):
    command.upgrade(alembic_config, "head")

    cols = {c["name"]: c for c in inspect(engine).get_columns("tasks")}
    assert set(cols) == {"id", "title", "description", "project_id", "state_id"}
    assert cols["title"]["nullable"] is False
    assert cols["description"]["nullable"] is True
    assert cols["project_id"]["nullable"] is False
    assert cols["state_id"]["nullable"] is False

    pk = tuple(inspect(engine).get_pk_constraint("tasks")["constrained_columns"])
    assert pk == ("id",)


def test_claves_foraneas_con_restrict(engine, alembic_config):
    command.upgrade(alembic_config, "head")

    fks = inspect(engine).get_foreign_keys("tasks")
    por_columna = {tuple(fk["constrained_columns"]): fk for fk in fks}

    assert ("project_id",) in por_columna
    assert por_columna[("project_id",)]["referred_table"] == "projects"
    assert por_columna[("project_id",)]["referred_columns"] == ["id"]
    assert por_columna[("project_id",)]["options"].get("ondelete") == "RESTRICT"

    assert ("state_id",) in por_columna
    assert por_columna[("state_id",)]["referred_table"] == "states"
    assert por_columna[("state_id",)]["referred_columns"] == ["id"]
    assert por_columna[("state_id",)]["options"].get("ondelete") == "RESTRICT"


def test_downgrade_quita_tasks_y_conserva_projects_y_states(engine, alembic_config):
    command.upgrade(alembic_config, "head")
    tablas = set(inspect(engine).get_table_names())
    assert {"tasks", "projects", "states"} <= tablas

    command.downgrade(alembic_config, "-1")
    tablas = set(inspect(engine).get_table_names())
    assert "tasks" not in tablas
    assert {"projects", "states"} <= tablas
