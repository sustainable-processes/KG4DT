from __future__ import annotations

from typing import Optional
from pydantic import Field

from .types import V1BaseModel


class CategoryBase(V1BaseModel):
    name: Optional[str] = Field(default=None, max_length=50)


class CategoryCreate(CategoryBase):
    name: str = Field(max_length=50)


class CategoryUpdate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    id: int
