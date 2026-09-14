"""Endpoints de `/projects` (ver `docs/contrato-api.md` §Proyectos)."""

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select, text

from app.deps import SessionDep
from app.errors import get_or_404
from app.models import Project
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate

# Respuestas de error para las operaciones sobre `/projects/{id}`
# (docs/contrato-api.md §Convenciones y §Proyectos).
_404 = {404: {"description": "Proyecto no encontrado"}}
_404_409 = {**_404, 409: {"description": "El proyecto tiene tareas"}}

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, session: SessionDep) -> Project:
    project = Project(name=payload.name, description=payload.description)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(session: SessionDep) -> list[Project]:
    stmt = select(Project).order_by(Project.id)
    return list(session.scalars(stmt))


@router.get("/{project_id}", response_model=ProjectOut, responses=_404)
def get_project(project_id: int, session: SessionDep) -> Project:
    return get_or_404(session, Project, project_id, "Proyecto no encontrado")


@router.patch("/{project_id}", response_model=ProjectOut, responses=_404)
def patch_project(
    project_id: int, payload: ProjectUpdate, session: SessionDep
) -> Project:
    project = get_or_404(session, Project, project_id, "Proyecto no encontrado")
    cambios = payload.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(project, campo, valor)
    session.commit()
    session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204, responses=_404_409)
def delete_project(project_id: int, session: SessionDep) -> Response:
    project = get_or_404(session, Project, project_id, "Proyecto no encontrado")
    tiene_tareas = session.scalar(
        text("SELECT 1 FROM tasks WHERE project_id = :pid LIMIT 1"),
        {"pid": project_id},
    )
    if tiene_tareas:
        raise HTTPException(
            status_code=409, detail="El proyecto tiene tareas y no se puede borrar"
        )
    session.delete(project)
    session.commit()
    return Response(status_code=204)
