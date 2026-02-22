from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ParamLawFilters(BaseModel):
    """JSON body schema for /api/exploration/pheno/param_law (POST).

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
    """JSON body for /api/exploration/info (or /api/v1/exploration/info).

    Used to specify the modeling context (species, phenomena, etc.) to retrieve
    relevant parameters for simulation or calibration.
    """

    # Legacy/translated format
    basic: Optional[Dict[str, Any]] = Field(default=None, description="Basic entities (stm, gas, sld, spc)")
    desc: Optional[Dict[str, Any]] = Field(default=None, description="Phenomena descriptors (ac, fp, mt, me, rxn, param_law)")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Wrapped context object (for backward compatibility)")

    # New frontend JSON format (top-level keys)
    type: Optional[str] = Field(default=None, description="Model type (e.g., steady/dynamic)")
    reactor: Optional[Dict[str, Any]] = Field(default=None, description="Reactor block")
    input: Optional[Dict[str, Any]] = Field(default=None, description="Input block")
    utility: Optional[Dict[str, Any]] = Field(default=None, description="Utility block")
    chemistry: Optional[Dict[str, Any]] = Field(default=None, description="Chemistry block")
    kinetics: Optional[List[Dict[str, Any]]] = Field(default=None, description="Kinetics block")
    model: Optional[Dict[str, Any]] = Field(default=None, description="Model block")

    model_config = {
        "json_schema_extra": {
            "example": {
                "basic": {"stm": {"S1": {"spc": ["A"]}}},
                "desc": {"ac": "Batch", "fp": "Well_Mixed"}
            }
        }
    }
