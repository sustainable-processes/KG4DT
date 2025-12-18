from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import Field

from .types import V1BaseModel, JsonDict


class ProjectBase(V1BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    content: JsonDict | None = None


class ProjectCreate(ProjectBase):
    name: str = Field(max_length=100)
    # Create by email only
    email: str = Field(min_length=1)


class ProjectUpdate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class ProjectListItem(V1BaseModel):
    id: int
    name: str
