"""Esquemas de entrada y de respuesta de la API (ver `docs/contrato-api.md`)."""

from pydantic import BaseModel, ConfigDict, field_validator


class StateOut(BaseModel):
    """Estado tal como lo devuelve `GET /states`: `id` y `code`, ni un campo más."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    code: str


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
