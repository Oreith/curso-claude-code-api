"""Modelos ORM mapeados a las tablas que crean las migraciones de Alembic.

Estas clases no crean ni alteran esquema: solo describen tablas que ya existen.
"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class State(Base):
    """Catálogo cerrado de estados. Solo lectura desde la API."""

    __tablename__ = "states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)


class Project(Base):
    """Proyecto. Campos del contrato: `id`, `name`, `description` opcional."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)


class Task(Base):
    """Tarea v1. Campos del contrato: `id`, `title`, `description` opcional,
    `project_id`, `state_id`. `due_at` llega en Tareas v2."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    state_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("states.id", ondelete="RESTRICT"), nullable=False
    )
