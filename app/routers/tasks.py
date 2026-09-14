"""Endpoints de `/tasks` (ver `docs/contrato-api.md` §Tareas v1, v2 y v3)."""

from typing import Literal

from fastapi import APIRouter, Response
from sqlalchemy import func, select

from app.deps import SessionDep
from app.errors import get_or_404, valida_referencia
from app.models import Project, State, Task
from app.schemas import TaskCreate, TaskOut, TaskUpdate

# Respuesta de error para las operaciones sobre `/tasks/{id}`
# (docs/contrato-api.md §Convenciones: `404` para recurso inexistente).
_404 = {404: {"description": "Tarea no encontrada"}}

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, session: SessionDep) -> Task:
    valida_referencia(
        session,
        Project,
        payload.project_id,
        "project_id no corresponde a ningún proyecto",
    )
    valida_referencia(
        session, State, payload.state_id, "state_id no corresponde a ningún estado"
    )
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


@router.get(
    "",
    response_model=list[TaskOut],
    summary="Lista las tareas ordenadas por id, con filtros opcionales",
)
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


@router.get("/{task_id}", response_model=TaskOut, responses=_404)
def get_task(task_id: int, session: SessionDep) -> Task:
    return get_or_404(session, Task, task_id, "Tarea no encontrada")


@router.patch("/{task_id}", response_model=TaskOut, responses=_404)
def patch_task(task_id: int, payload: TaskUpdate, session: SessionDep) -> Task:
    task = get_or_404(session, Task, task_id, "Tarea no encontrada")
    cambios = payload.model_dump(exclude_unset=True)
    if "project_id" in cambios:
        valida_referencia(
            session,
            Project,
            cambios["project_id"],
            "project_id no corresponde a ningún proyecto",
        )
    if "state_id" in cambios:
        valida_referencia(
            session,
            State,
            cambios["state_id"],
            "state_id no corresponde a ningún estado",
        )
    for campo, valor in cambios.items():
        setattr(task, campo, valor)
    session.commit()
    session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204, responses=_404)
def delete_task(task_id: int, session: SessionDep) -> Response:
    task = get_or_404(session, Task, task_id, "Tarea no encontrada")
    session.delete(task)
    session.commit()
    return Response(status_code=204)
