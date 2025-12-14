from __future__ import annotations

from typing import Optional
from pydantic import Field

from .types import V2BaseModel, JsonDict


class ExperimentDataBase(V2BaseModel):
    project_id: Optional[int] = None
    data: JsonDict | None = None


class ExperimentDataCreate(ExperimentDataBase):
    project_id: int
    data: JsonDict | None = Field(default_factory=dict)


class ExperimentDataUpdate(ExperimentDataBase):
    pass


class ExperimentDataRead(ExperimentDataBase):
    id: int
    created_at: str
    updated_at: str
