from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import Field

from .types import V1BaseModel, JsonDict


class ReactorJsonData(V1BaseModel):
    """Deprecated: previously used as the type of `json_data` in read responses.

    Kept for backward compatibility in code references, but the API no longer
    returns a `json_data` wrapper. The flattened fields (`reactor`, `input`,
    `utility`) are now at the top level of `ReactorRead`.
    """

    reactor: JsonDict = Field(default_factory=dict, description="Reactor block stored in DB")
    input: JsonDict | None = Field(default=None, description="Computed from associated Basics with usage='inlet'")
    utility: JsonDict | None = Field(default=None, description="Computed from associated Basics with usage='utilities'")


class ReactorBase(V1BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    number_of_input: Optional[int] = 0
    number_of_output: Optional[int] = 0
    icon_url: Optional[str] = Field(default=None, max_length=255)
    reactor: JsonDict | None = Field(default=None, description="Reactor block persisted in DB")
    chemistry: JsonDict | None = None
    kinetics: JsonDict | None = None


class ReactorCreate(ReactorBase):
    name: str = Field(max_length=100)


class ReactorUpdate(ReactorBase):
    pass


class ReactorRead(V1BaseModel):
    id: int
    name: str
    number_of_input: int
    number_of_output: int
    icon_url: Optional[str] = None
    # Flattened fields (no json_data wrapper in read responses)
    reactor: JsonDict = Field(default_factory=dict, description="Reactor block stored in DB")
    input: JsonDict | None = Field(default=None, description="Computed from associated Basics with usage='inlet'")
    utility: JsonDict | None = Field(default=None, description="Computed from associated Basics with usage='utilities'")
    chemistry: JsonDict | None = None
    kinetics: JsonDict | None = None
    created_at: datetime
    updated_at: datetime


class ReactorBrief(V1BaseModel):
    id: int
    name: str
