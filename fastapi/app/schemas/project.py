from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class ProjectBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(default=None, max_length=255)
    user_id: Optional[int] = None
    model: Optional[str] = Field(default=None, max_length=255)
    content: Optional[dict[str, Any]] = None


class ProjectCreate(ProjectBase):
    name: str = Field(max_length=255)


class ProjectUpdate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: int
    datetime: datetime
    last_update: datetime