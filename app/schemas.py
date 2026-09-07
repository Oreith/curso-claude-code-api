"""Esquemas de entrada y de respuesta de la API (ver `docs/contrato-api.md`)."""

import unicodedata

from pydantic import BaseModel, ConfigDict, field_validator

# Categorías Unicode sin carácter visible (docs/contrato-api.md §Normalización).
_CATEGORIAS_INVISIBLES = {"Cc", "Cf", "Zl", "Zp", "Zs"}


class StateOut(BaseModel):
    """Estado tal como lo devuelve `GET /states`: `id` y `code`, ni un campo más."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    code: str


def _titulo_normalizado(value: str) -> str:
    """Recorta `title` y rechaza el valor sin ningún carácter visible (`422`).

    No basta con `strip()`: se rechaza si, tras recortar, todos los caracteres
    caen en `Cc`, `Cf`, `Zl`, `Zp` o `Zs`. Los invisibles interiores de un
    título con algún carácter visible se conservan.
    """
    recortado = value.strip()
    if not any(
        unicodedata.category(ch) not in _CATEGORIAS_INVISIBLES for ch in recortado
    ):
        raise ValueError("title no puede quedar sin ningún carácter visible")
    return recortado


def _name_limpio(value: str) -> str:
    """Recorta los extremos y rechaza el nombre que queda vacío (`422`)."""
    recortado = value.strip()
    if not recortado:
        raise ValueError("name no puede quedar vacío")
    return recortado


class ProjectCreate(BaseModel):
    """Cuerpo de `POST /projects`."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None

    _valida_name = field_validator("name")(_name_limpio)


class ProjectUpdate(BaseModel):
    """Cuerpo de `PATCH /projects/{id}`: actualización parcial.

    Solo se modifican los campos presentes en el cuerpo. `description` puede
    ponerse a `null` explícitamente; `name`, si viene, no puede quedar vacío.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def _valida_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _name_limpio(value)


class ProjectOut(BaseModel):
    """Proyecto tal como lo devuelve la API: `id`, `name`, `description`, nada más."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    name: str
    description: str | None


class TaskCreate(BaseModel):
    """Cuerpo de `POST /tasks` (v1)."""

    model_config = ConfigDict(extra="forbid")

    title: str
    description: str | None = None
    project_id: int
    state_id: int

    _valida_title = field_validator("title")(_titulo_normalizado)


class TaskUpdate(BaseModel):
    """Cuerpo de `PATCH /tasks/{id}`: actualización parcial consistente.

    Solo se modifican los campos presentes. `title`, si viene, se normaliza y no
    puede quedar sin carácter visible. `description` admite `null` explícito.
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    project_id: int | None = None
    state_id: int | None = None

    @field_validator("title")
    @classmethod
    def _valida_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _titulo_normalizado(value)


class TaskOut(BaseModel):
    """Tarea tal como la devuelve la API (v1): cinco campos, ni uno más."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    title: str
    description: str | None
    project_id: int
    state_id: int
