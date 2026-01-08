from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ParamLawFilters(BaseModel):
    """JSON body schema for /api/model/pheno/param_law (POST).

    Accepts phenomenon selections to constrain parameter-to-law mapping.
    Values can be a single string or a list of strings.
    """

    ac: Optional[Union[str, List[str]]] = Field(default=None, description="Accumulation (e.g., 'Batch' or 'Continuous')")
    fp: Optional[Union[str, List[str]]] = Field(default=None, description="Flow pattern name(s)")
    mt: Optional[Union[str, List[str]]] = Field(default=None, description="Mass transport phenomenon name(s)")
    me: Optional[Union[str, List[str]]] = Field(default=None, description="Mass equilibrium phenomenon name(s)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "fp": "Well_Mixed",
                "mt": ["Engulfment"],
                "me": ["Gas_Dissolution_Equilibrium"],
            }
        }
    }

class InfoContext(BaseModel):
    """Optional JSON body for GET /api/model/info.

    Currently unused for filtering, but accepted for forward compatibility.
    """

    context: Optional[Dict[str, Any]] = Field(default=None, description="Context object reserved for future use")

    model_config = {
        "json_schema_extra": {
            "example": {"context": {}}
        }
    }
