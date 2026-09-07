"""Migración de la tabla `projects`, contra el PostgreSQL real de Compose.

Comprobación del Incremento 1:

- tras `upgrade head`, `projects` tiene exactamente las columnas `id`, `name` y
  `description`, con la nulabilidad correcta y `id` como clave primaria;
- `downgrade` elimina la tabla y `upgrade` la reconstruye idéntica.

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
    """Deja la base sin ninguna tabla: revierte y borra todo lo que quede."""
    command.downgrade(alembic_config, "base")
    with engine.begin() as conn:
        for tabla in inspect(conn).get_table_names():
            conn.execute(text(f'DROP TABLE IF EXISTS "{tabla}" CASCADE'))


@pytest.fixture(autouse=True)
def base_limpia(engine, alembic_config):
    _reset_base(engine, alembic_config)
    yield
    _reset_base(engine, alembic_config)


def _columns(engine) -> dict:
    return {c["name"]: c for c in inspect(engine).get_columns("projects")}


def _shape(engine) -> dict:
    """Vista estable de la tabla: tipo (como texto) y nulabilidad por columna."""
    return {
        nombre: (str(col["type"]), col["nullable"])
        for nombre, col in _columns(engine).items()
    }


def test_upgrade_crea_projects_con_columnas_exactas(engine, alembic_config):
    command.upgrade(alembic_config, "head")

    assert "projects" in inspect(engine).get_table_names()

    cols = _columns(engine)
    assert set(cols) == {"id", "name", "description"}
    assert cols["name"]["nullable"] is False
    assert cols["description"]["nullable"] is True

    pk = tuple(inspect(engine).get_pk_constraint("projects")["constrained_columns"])
    assert pk == ("id",)


def test_downgrade_elimina_projects_y_upgrade_la_reconstruye(engine, alembic_config):
    command.upgrade(alembic_config, "head")
    original = _shape(engine)
    assert original

    command.downgrade(alembic_config, "base")
    assert "projects" not in inspect(engine).get_table_names()

    command.upgrade(alembic_config, "head")
    assert _shape(engine) == original
