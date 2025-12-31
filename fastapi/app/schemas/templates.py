from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import Field

from .types import V1BaseModel
from .reactors import ReactorBrief


class TemplateBase(V1BaseModel):
    category_id: Optional[int] = None
    reactor_id: Optional[int] = None


class TemplateCreate(TemplateBase):
    category_id: int
    reactor_id: int


class TemplateUpdate(TemplateBase):
    pass


class TemplateRead(TemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime


class GeneralTemplateName(V1BaseModel):
    name: str


class ReactorTile(V1BaseModel):
    id: int
    name: str
    icon: Optional[str] = None


class GeneralTemplateItem(V1BaseModel):
    id: Optional[int] = None
    name: str
    icon: Optional[str] = None
    type: Optional[str] = None
    tab_type: Optional[str] = None


class AssemblyTemplatesResponse(V1BaseModel):
    # Top-level keys as requested by the client
    Templates: List[ReactorTile]
    Tutorials: List[ReactorTile]
    General: List[GeneralTemplateItem]
