from __future__ import annotations

from typing import Optional
from pydantic import Field

from .types import V2BaseModel, BasicMatterType, BasicUsage


class BasicBase(V2BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    type: Optional[BasicMatterType] = None
    usage: Optional[BasicUsage] = None
    structure: Optional[str] = Field(default=None, max_length=100)
    phase: Optional[str] = Field(default=None, max_length=50)
    operation: Optional[str] = Field(default=None, max_length=50)


class BasicCreate(BasicBase):
    name: str = Field(max_length=100)
    type: BasicMatterType
    usage: BasicUsage


class BasicUpdate(BasicBase):
    pass


class BasicRead(BasicBase):
    id: int
    created_at: str
    updated_at: str
