from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class ReactorBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(default=None, max_length=255)
    number_of_input: Optional[int] = Field(default=None, ge=0)
    number_of_output: Optional[int] = Field(default=None, ge=0)
    icon: Optional[str] = Field(default=None, max_length=255)
    species: Optional[dict[str, Any]] = None


class ReactorCreate(ReactorBase):
    name: str = Field(max_length=255)
    number_of_input: int = Field(default=0, ge=0)
    number_of_output: int = Field(default=0, ge=0)


class ReactorUpdate(ReactorBase):
    pass


class ReactorRead(ReactorBase):
    id: int
    created_date: datetime