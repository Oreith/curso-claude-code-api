"""Endpoints de `/tasks` (ver `docs/contrato-api.md` §Tareas v1, v2 y v3)."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import SessionDep
from app.models import Project, State, Task
from app.schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Conjunto cerrado de prioridades (docs/contrato-api.md §Tareas v3).
_PRIORIDADES = {"BAJA", "MEDIA", "ALTA"}


def _task_o_404(session: Session, task_id: int) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return task


def _valida_project_id(session: Session, project_id: int) -> None:
    if session.get(Project, project_id) is None:
        raise HTTPException(
            status_code=422, detail="project_id no corresponde a ningún proyecto"
        )


def _valida_state_id(session: Session, state_id: int) -> None:
    if session.get(State, state_id) is None:
        raise HTTPException(
            status_code=422, detail="state_id no corresponde a ningún estado"
        )


def _valida_priority(value: str | None) -> None:
    if value is not None and value not in _PRIORIDADES:
        raise HTTPException(
            status_code=422,
            detail="priority debe ser uno de BAJA, MEDIA o ALTA",
        )


@router.post("", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, session: SessionDep) -> Task:
    _valida_project_id(session, payload.project_id)
    _valida_state_id(session, payload.state_id)
    _valida_priority(payload.priority)
    task = Task(
        title=payload.title,
        description=payload.description,
        project_id=payload.project_id,
        state_id=payload.state_id,
        due_at=payload.due_at,
        priority=payload.priority,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(
    session: SessionDep,
    project_id: int | None = None,
    state_id: int | None = None,
    overdue: Literal["true", "false"] | None = None,
) -> list[Task]:
    stmt = select(Task)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if state_id is not None:
        stmt = stmt.where(Task.state_id == state_id)
    if overdue == "true":
        hecha_id = session.scalar(select(State.id).where(State.code == "HECHA"))
        stmt = stmt.where(
            Task.due_at.is_not(None),
            Task.due_at < func.now(),
            Task.state_id != hecha_id,
        )
    stmt = stmt.order_by(Task.id)
    return list(session.scalars(stmt))


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, session: SessionDep) -> Task:
    return _task_o_404(session, task_id)


@router.patch("/{task_id}", response_model=TaskOut)
def patch_task(task_id: int, payload: TaskUpdate, session: SessionDep) -> Task:
    task = _task_o_404(session, task_id)
    cambios = payload.model_dump(exclude_unset=True)
    if "project_id" in cambios:
        _valida_project_id(session, cambios["project_id"])
    if "state_id" in cambios:
        _valida_state_id(session, cambios["state_id"])
    if "priority" in cambios:
        _valida_priority(cambios["priority"])
    for campo, valor in cambios.items():
        setattr(task, campo, valor)
    session.commit()
    session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, session: SessionDep) -> Response:
    task = _task_o_404(session, task_id)
    session.delete(task)
    session.commit()
    return Response(status_code=204)
