from __future__ import annotations

from typing import Optional
from pydantic import Field

from .types import V2BaseModel, JsonDict


class ModelBase(V2BaseModel):
    project_id: Optional[int] = None
    name: Optional[str] = Field(default=None, max_length=100)
    mt: list[str] | None = None
    me: list[str] | None = None
    laws: JsonDict | None = None


class ModelCreate(ModelBase):
    project_id: int
    name: str = Field(max_length=100)


class ModelUpdate(ModelBase):
    pass


class ModelRead(ModelBase):
    id: int
    created_at: str
    updated_at: str
