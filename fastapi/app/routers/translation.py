from __future__ import annotations

from fastapi import APIRouter, Body
from ..schemas.translation import FrontendPayload, TranslationResponse
from ..utils.frontend_translation import translate_frontend_to_backend
from ..utils.mml_expression import MMLExpression


router = APIRouter(prefix="/api/v1", tags=["v1: translate"])


@router.post("/translate_frontend_json", response_model=TranslationResponse)
def translate_frontend_json(payload: FrontendPayload) -> TranslationResponse:
    """Translate frontend JSON into backend context structure.

    This endpoint maps frontend-specific data structures (chemistry, input, phenomenon)
    into the standard backend `context` format used by simulation and calibration agents.
    """
    context = translate_frontend_to_backend(payload)
    return TranslationResponse(context=context)


@router.post("/translate_mathml")
def translate_mathml(
    mathml: str = Body(..., embed=True, description="MathML string to translate")
):
    """Translate a MathML string into a human-readable format (NumPy-like)."""
    translated = MMLExpression.translate(mathml)
    if translated is None:
        return {"error": "Failed to translate MathML"}
    return {"translated": translated}


# ---------------------- KG -> Frontend translation ----------------------
"""KG→Frontend translation logic is now directly handled in the kg_components router
by flattening the KG context template details. The endpoints are exposed under
/api/v1/kg_components/{name} and /api/assembly/kg_components/{name}."""
