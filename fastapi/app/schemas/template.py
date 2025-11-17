from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class TemplateBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: Optional[str] = Field(default=None, max_length=255)
    reactor_id: Optional[int] = None


class TemplateCreate(TemplateBase):
    category: str = Field(max_length=255)
    reactor_id: int


class TemplateUpdate(TemplateBase):
    pass


class TemplateRead(TemplateBase):
    id: int
