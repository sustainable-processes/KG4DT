from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class SpeciesRoleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(default=None, max_length=255)
    attribute: Optional[str] = Field(default=None, max_length=255)


class SpeciesRoleCreate(SpeciesRoleBase):
    name: str = Field(max_length=255)


class SpeciesRoleUpdate(SpeciesRoleBase):
    pass


class SpeciesRoleRead(SpeciesRoleBase):
    id: int