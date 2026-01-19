from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import Field

from .types import V1BaseModel, JsonDict


class ExperimentDataBase(V1BaseModel):
    project_id: Optional[int] = None
    model_id: Optional[int] = None
    data: JsonDict | None = None


class ExperimentDataCreate(ExperimentDataBase):
    project_id: int
    model_id: int
    data: JsonDict | None = Field(default_factory=dict)


class ExperimentDataUpdate(ExperimentDataBase):
    pass


class ExperimentDataRead(ExperimentDataBase):
    id: int
    created_at: datetime
    updated_at: datetime
