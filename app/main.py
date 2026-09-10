import tomllib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import select

from app.db import make_engine, make_sessionmaker
from app.deps import SessionDep, set_sessionmaker
from app.models import State
from app.routers import projects, tasks
from app.schemas import StateOut


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = make_engine()
    set_sessionmaker(make_sessionmaker(engine))
    try:
        yield
    finally:
        set_sessionmaker(None)
        engine.dispose()


def _version() -> str:
    """Versión declarada en `pyproject.toml` (el paquete no se instala como dist)."""
    datos = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())
    return datos["project"]["version"]


app = FastAPI(title="TaskFlow API", version=_version(), lifespan=lifespan)
app.include_router(projects.router)
app.include_router(tasks.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/states", response_model=list[StateOut])
def list_states(session: SessionDep) -> list[State]:
    stmt = select(State).order_by(State.position, State.id)
    return list(session.scalars(stmt))
