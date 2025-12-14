from __future__ import annotations

from typing import List, Dict

import re
from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(prefix="/models", tags=["validation"])  # business-logic validation endpoints


class ValidateSpeciesRequest(BaseModel):
    stoichiometric: List[str] = Field(default_factory=list, description="List of stoichiometric strings, e.g. 'A + B = C'")
    species_id: List[str] = Field(default_factory=list, description="Initial list of species IDs")


class ValidateSpeciesResponse(BaseModel):
    species_id: List[str]


_LEADING_COEFF_RE = re.compile(r"^\s*(?:\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*")


def _normalize_token(token: str) -> str | None:
    """Normalize a stoichiometric token to a species name.

    Rules:
    - Trim whitespace and surrounding parentheses.
    - Drop a leading numeric coefficient (e.g., '2B' -> 'B', '0.5 C' -> 'C').
    - Return None for empty/invalid tokens.
    """
    if token is None:
        return None
    s = token.strip()
    if not s:
        return None
    # Remove surrounding parentheses like '(A)'
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()
    # Remove a leading numeric coefficient (supports integers, decimals, scientific)
    s = _LEADING_COEFF_RE.sub("", s, count=1)
    s = s.strip()
    if not s:
        return None
    # Keep only basic species id characters: letters, numbers, underscore
    # This matches common names like A, B, H2, C6H6, Species_1
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", s):
        return None
    return s


@router.post("/validate_species/", response_model=ValidateSpeciesResponse)
def validate_species(payload: ValidateSpeciesRequest) -> ValidateSpeciesResponse:
    """Validate and augment species_id using stoichiometric expressions.

    Example:
      Input:  {"stoichiometric": ["A + B = C", "2B + C = D"], "species_id": ["A", "B"]}
      Output: {"species_id": ["A", "B", "C", "D"]}

    Logic: Every species appearing in any stoichiometric expression must be present in species_id.
    Numeric coefficients are ignored (e.g., '2B' contributes 'B').
    Order is preserved: start with the provided species_id, then append new species in first-seen order.
    """
    # Preserve order with a set for O(1) membership
    out: List[str] = []
    seen = set()

    # Seed with provided species_id (normalized to the same pattern used for tokens if valid)
    for s in payload.species_id:
        if isinstance(s, str):
            s_norm = s.strip()
            if re.match(r"^[A-Za-z][A-Za-z0-9_]*$", s_norm) and s_norm not in seen:
                seen.add(s_norm)
                out.append(s_norm)

    # Parse stoichiometric expressions
    for expr in payload.stoichiometric or []:
        if not isinstance(expr, str):
            continue
        # Split on '=' and '+'
        parts = re.split(r"[=+]", expr)
        for part in parts:
            sp = _normalize_token(part)
            if sp and sp not in seen:
                seen.add(sp)
                out.append(sp)

    return ValidateSpeciesResponse(species_id=out)
