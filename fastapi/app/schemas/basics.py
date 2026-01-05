from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import Field

from .types import V1BaseModel, BasicMatterType, BasicUsage, JsonDict


class BasicBase(V1BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    type: Optional[BasicMatterType] = None
    usage: Optional[BasicUsage] = None
    structure: JsonDict | None = None
    phase: JsonDict | None = None
    operation: JsonDict | None = None


class BasicCreate(BasicBase):
    name: str = Field(max_length=100)
    type: BasicMatterType
    usage: BasicUsage


class BasicUpdate(BasicBase):
    pass


class BasicRead(BasicBase):
    id: int
    created_at: datetime
    updated_at: datetime
