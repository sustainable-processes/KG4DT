from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class V2BaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BasicMatterType(str, Enum):
    steam = "steam"
    solid = "solid"
    gas = "gas"


class BasicUsage(str, Enum):
    inlet = "inlet"
    outlet = "outlet"
    utilities = "utilities"


# Common field types
JsonDict = dict[str, Any]
