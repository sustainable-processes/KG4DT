from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


from pydantic import BaseModel, Field, ConfigDict


class BasicBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(default=None, max_length=255)
    size: Optional[float] = None
    substance: Optional[str] = Field(default=None, max_length=255)
    time: Optional[float] = None
    pressure: Optional[float] = None
    temperature: Optional[float] = None
    structure: Optional[dict[str, Any]] = None


class BasicCreate(BasicBase):
    # For creation, name is required
    name: str = Field(max_length=255)


class BasicUpdate(BasicBase):
    # All fields optional
    pass


class BasicRead(BasicBase):
    id: int
