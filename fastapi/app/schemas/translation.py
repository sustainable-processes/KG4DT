from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FrontendPayload(BaseModel):
    """Schema for the frontend JSON payload."""
    name: Optional[str] = None
    number_of_input: Optional[int] = None
    number_of_output: Optional[int] = None
    icon_url: Optional[str] = None
    reactor: Optional[Dict[str, Any]] = Field(default_factory=dict)
    input: Optional[Dict[str, Any]] = Field(default_factory=dict)
    utility: Optional[Dict[str, Any]] = Field(default_factory=dict)
    chemistry: Optional[Dict[str, Any]] = Field(default_factory=dict)
    kinetics: Optional[Any] = Field(default_factory=dict)
    model: Optional[Dict[str, Any]] = Field(default_factory=dict)
    phenomenon: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Phenomena selections (ac, fp, mt, me)")


class BackendContextBasic(BaseModel):
    """Schema for the `basic` section of the backend context."""
    spc: List[Dict[str, Any]] = Field(default_factory=list)
    rxn: List[Dict[str, Any]] = Field(default_factory=list)
    stm: Dict[str, Any] = Field(default_factory=dict)
    sld: Dict[str, Any] = Field(default_factory=dict)
    gas: Dict[str, Any] = Field(default_factory=dict)


class BackendContextDesc(BaseModel):
    """Schema for the `desc` section of the backend context."""
    ac: Optional[str] = None
    fp: Optional[str] = None
    mt: List[str] = Field(default_factory=list)
    me: List[str] = Field(default_factory=list)
    rxn: Dict[str, List[str]] = Field(default_factory=dict)
    param_law: Dict[str, str] = Field(default_factory=dict)


class BackendContext(BaseModel):
    """Schema for the full backend context."""
    type: str = "dynamic"
    basic: BackendContextBasic
    desc: Optional[BackendContextDesc] = None
    info: Dict[str, Any] = Field(default_factory=dict)


class TranslationResponse(BaseModel):
    """Response schema for the translation endpoint."""
    context: BackendContext


