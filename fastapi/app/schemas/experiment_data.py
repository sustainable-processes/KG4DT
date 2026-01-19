from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Any
from pydantic import Field, model_validator

from .types import V1BaseModel


class ExperimentDataContent(V1BaseModel):
    op_param: List[List[Optional[str]]] = Field(..., description="List of 5-tuple parameter headers")
    rows: List[List[Any]] = Field(..., description="List of data rows")

    @model_validator(mode="after")
    def validate_dimensions(self) -> "ExperimentDataContent":
        if not self.op_param:
            return self
        col_count = len(self.op_param)
        for i, row in enumerate(self.rows):
            if len(row) != col_count:
                raise ValueError(
                    f"Row {i} has {len(row)} values, but {col_count} headers are defined."
                )
        return self


class ExperimentDataBase(V1BaseModel):
    project_id: Optional[int] = None
    model_id: Optional[int] = None
    name: Optional[str] = Field(default=None, max_length=100)
    data: ExperimentDataContent | None = None


class ExperimentDataCreate(ExperimentDataBase):
    project_id: int
    model_id: int
    data: ExperimentDataContent | None = None


class ExperimentDataUpdate(ExperimentDataBase):
    pass


class ExperimentDataRead(ExperimentDataBase):
    id: int
    created_at: datetime
    updated_at: datetime
