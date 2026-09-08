"""Migraciones de la tabla `tasks`, contra el PostgreSQL de Compose.

- tras `upgrade head`, `tasks` tiene exactamente `id`, `title`, `description`,
  `project_id`, `state_id` y `due_at` (v2), con la nulabilidad correcta;
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


def test_columnas_de_tasks(engine, alembic_config):
    command.upgrade(alembic_config, "head")

    cols = {c["name"]: c for c in inspect(engine).get_columns("tasks")}
    assert set(cols) == {
        "id",
        "title",
        "description",
        "project_id",
        "state_id",
        "due_at",
        "priority",
    }
    assert cols["title"]["nullable"] is False
    assert cols["description"]["nullable"] is True
    assert cols["project_id"]["nullable"] is False
    assert cols["state_id"]["nullable"] is False
    assert cols["due_at"]["nullable"] is True
    assert "TIMESTAMP" in str(cols["due_at"]["type"]).upper()
    assert cols["priority"]["nullable"] is True

    pk = tuple(inspect(engine).get_pk_constraint("tasks")["constrained_columns"])
    assert pk == ("id",)


def test_priority_check_constraint(engine, alembic_config):
    command.upgrade(alembic_config, "head")

    checks = {
        c["name"]: c.get("sqltext", "")
        for c in inspect(engine).get_check_constraints("tasks")
    }
    assert "ck_tasks_priority" in checks
    sql = checks["ck_tasks_priority"].upper()
    for valor in ("BAJA", "MEDIA", "ALTA"):
        assert valor in sql


def test_rollback_de_v3_y_v2_conserva_el_resto(engine, alembic_config):
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "-1")  # revierte priority (rollback v3)

    cols = {c["name"] for c in inspect(engine).get_columns("tasks")}
    assert cols == {"id", "title", "description", "project_id", "state_id", "due_at"}

    command.downgrade(alembic_config, "-1")  # revierte due_at (rollback v2)
    cols = {c["name"] for c in inspect(engine).get_columns("tasks")}
    assert cols == {"id", "title", "description", "project_id", "state_id"}
    fks = inspect(engine).get_foreign_keys("tasks")
    assert {tuple(fk["constrained_columns"]) for fk in fks} == {
        ("project_id",),
        ("state_id",),
    }

    command.upgrade(alembic_config, "head")
    cols = {c["name"] for c in inspect(engine).get_columns("tasks")}
    assert {"due_at", "priority"} <= cols


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


def test_downgrade_de_tasks_quita_la_tabla_y_conserva_projects_y_states(
    engine, alembic_config
):
    command.upgrade(alembic_config, "head")
    assert {"tasks", "projects", "states"} <= set(inspect(engine).get_table_names())

    # Revierte priority (v3), due_at (v2) y luego la creación de tasks, sin ids fijos.
    command.downgrade(alembic_config, "-1")
    command.downgrade(alembic_config, "-1")
    command.downgrade(alembic_config, "-1")

    tablas = set(inspect(engine).get_table_names())
    assert "tasks" not in tablas
    assert {"projects", "states"} <= tablas
