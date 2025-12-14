from __future__ import annotations

from typing import Optional
from pydantic import Field

from .types import V2BaseModel, JsonDict


class ReactorBase(V2BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    number_of_input: Optional[int] = 0
    number_of_output: Optional[int] = 0
    icon_url: Optional[str] = Field(default=None, max_length=255)
    json_data: JsonDict | None = None
    chemistry: JsonDict | None = None
    kinetics: JsonDict | None = None


class ReactorCreate(ReactorBase):
    name: str = Field(max_length=100)


class ReactorUpdate(ReactorBase):
    pass


class ReactorRead(ReactorBase):
    id: int
    created_at: str
    updated_at: str
