from __future__ import annotations

from typing import Optional
from pydantic import Field

from .types import V2BaseModel


class TemplateBase(V2BaseModel):
    category_id: Optional[int] = None
    reactor_id: Optional[int] = None


class TemplateCreate(TemplateBase):
    category_id: int
    reactor_id: int


class TemplateUpdate(TemplateBase):
    pass


class TemplateRead(TemplateBase):
    id: int
    created_at: str
    updated_at: str
