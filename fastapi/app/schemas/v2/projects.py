from __future__ import annotations

from typing import Any, Optional
from pydantic import Field

from .types import V2BaseModel, JsonDict


class ProjectBase(V2BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    user_id: Optional[int] = None
    content: JsonDict | None = None


class ProjectCreate(ProjectBase):
    name: str = Field(max_length=100)
    user_id: int


class ProjectUpdate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: int
    created_at: str
    updated_at: str
