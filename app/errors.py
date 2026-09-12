"""Manejo de errores compartido por los routers (ver `docs/contrato-api.md`).

Centraliza las dos familias de error que los routers lanzan a mano con
`HTTPException` (no las que genera Pydantic/FastAPI en `app/schemas.py`, que
quedan fuera de este módulo a propósito):

- `404` cuando un recurso no existe (`get_or_404`).
- `422` cuando una referencia a otro recurso (`project_id`, `state_id`) no
  existe (`valida_referencia`).
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Base


def get_or_404[M: Base](
    session: Session, model: type[M], obj_id: int, mensaje: str
) -> M:
    """Devuelve la fila de `model` con clave primaria `obj_id`, o `404`.

    Reemplaza a `_get_or_404` (antes en `app/routers/projects.py`) y a
    `_task_o_404` (antes en `app/routers/tasks.py`), que eran idénticas salvo
    por el modelo y el mensaje.
    """
    obj = session.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=mensaje)
    return obj


def valida_referencia(
    session: Session, model: type[Base], ref_id: int, mensaje: str
) -> None:
    """Rechaza con `422` una referencia (`project_id`, `state_id`, ...) que no
    corresponde a ninguna fila de `model`.

    Reemplaza a `_valida_project_id` y `_valida_state_id` (antes en
    `app/routers/tasks.py`), que solo variaban en el modelo y el mensaje.
    """
    if session.get(model, ref_id) is None:
        raise HTTPException(status_code=422, detail=mensaje)
