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


class RxnFilters(BaseModel):
    """Optional JSON body schema for GET /api/model/pheno/rxn.

    All fields are optional. If no fields provided, the API returns all reactions.
    """

    ac: Optional[Union[str, List[str]]] = Field(default=None, description="Accumulation filter(s)")
    fp: Optional[Union[str, List[str]]] = Field(default=None, description="Flow pattern filter(s)")
    mt: Optional[Union[str, List[str]]] = Field(default=None, description="Mass transport filter(s)")
    me: Optional[Union[str, List[str]]] = Field(default=None, description="Mass equilibrium filter(s)")
    param: Optional[Union[str, List[str]]] = Field(default=None, description="Parameter/variable filter(s)")
    law: Optional[Union[str, List[str]]] = Field(default=None, description="Law name filter(s)")
    param_law: Optional[Any] = Field(default=None, description="Parameter-to-law mapping candidate(s)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "ac": "Batch",
                "fp": ["Well_Mixed"],
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
