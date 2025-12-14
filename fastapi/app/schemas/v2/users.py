from __future__ import annotations

from typing import Optional

from pydantic import Field

from .types import V2BaseModel


class UserBase(V2BaseModel):
    username: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)


class UserCreate(UserBase):
    username: str = Field(max_length=255)
    email: str = Field(max_length=255)


class UserUpdate(UserBase):
    pass


class UserRead(UserBase):
    id: int
    created_at: str
    updated_at: str
