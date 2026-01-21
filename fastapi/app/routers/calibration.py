from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Request

from ..schemas.experiment_data import ExperimentDataContent
from ..services.graphdb import GraphDBClient
from ..utils.graphdb_calibration_utils import (
    query_law as gq_query_law,
    query_symbol as gq_query_symbol,
    query_symbols as gq_query_symbols,
    build_triplets as gq_build_triplets,
    query_op_param as gq_query_op_param,
    normalize_context as gq_normalize_context,
)

router = APIRouter()


@router.get("/law")
async def get_model_law(request: Request) -> Dict[str, Any]:
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")
    try:
        return gq_query_law(client)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Failed to query laws from GraphDB", "detail": str(e)})


@router.post("/sym")
async def post_model_symbol(request: Request, body: Dict[str, Any] = Body(..., description="Provide unit or units to resolve symbols")) -> Dict[str, Any]:
    """Resolve symbols for one or more Unit individuals.

    Body examples:
      {"unit": "Pa"}
      {"units": ["Pa", "m", "s"]}
    """
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON body; expected an object.")

    units: List[str] = []

    def _add(val: Any) -> None:
        if val is None:
            return
        if isinstance(val, list):
            for x in val:
                _add(x)
        else:
            s = str(val).strip()
            if s:
                units.append(s)

    if "units" in body:
        _add(body.get("units"))
    if "unit" in body:
        _add(body.get("unit"))

    # de-dup while preserving order
    seen = set()
    uniq_units: List[str] = []
    for u in units:
        if u not in seen:
            seen.add(u)
            uniq_units.append(u)

    if not uniq_units:
        raise HTTPException(status_code=400, detail={
            "error": "No 'unit' or 'units' provided.",
            "hint": {"POST": {"units": ["Pa", "m"]}},
        })

    try:
        return gq_query_symbols(client, uniq_units)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Failed to resolve symbols", "detail": str(e)})


@router.get("/triplets")
async def get_knowledge_graph_triplets(request: Request) -> Dict[str, Any]:
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")
    try:
        return gq_build_triplets(client)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Failed to build knowledge graph triplets", "detail": str(e)})


# The following endpoints require deeper migration of Flask agents (ModelSimulationAgent, ModelCalibrationAgent, etc.).
# We expose POST-only endpoints with clear 501 responses to indicate planned work while keeping API shape compatible.


def _not_implemented(name: str) -> Dict[str, Any]:
    return {
        "error": "NotImplemented",
        "detail": f"{name} is not migrated yet. This endpoint expects a JSON body. Use the Flask service or plan migration of agents.",
    }


@router.post("/op_param", response_model=ExperimentDataContent)
async def post_model_op_param(request: Request, body: Dict[str, Any] = Body(..., description="Provide modeling context with 'basic' and 'desc'")):
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail={"error": "Invalid JSON body; expected an object."})

    # Accept either full context at top-level or under a top-level 'context' key
    context_in: Dict[str, Any] = body.get("context") if "context" in body else body
    if not isinstance(context_in, dict):
        raise HTTPException(status_code=400, detail={"error": "Field 'context' must be an object when provided."})

    # Normalize (reuse util) and compute OPs
    try:
        context_norm = gq_normalize_context(context_in)
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "Failed to normalize context", "detail": str(e)})

    try:
        entries = gq_query_op_param(client, context_norm)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Failed to derive operation parameters", "detail": str(e)})

    if not entries:
        raise HTTPException(status_code=404, detail={"error": "No operation parameters derived for the specified context.", "context": context_norm})

    return {"op_param": entries, "rows": []}


@router.post("/simulate")
async def post_model_simulate(_: Request, body: Dict[str, Any] = Body(..., description="Simulation request: {'context': {...}, 'op_params': {'ind': [...], 'val': [[...], ...]}}")) -> Dict[str, Any]:
    """Run a lightweight deterministic simulation over a table of experiments.

    This POST endpoint accepts JSON with:
      - context: object (required)
      - op_params: dataset-like object with 'ind' and 'val' (required)

    It returns a tabular result with the same indices as op_params.ind and a single
    simulated value per row computed from the input values (sum of numeric cells).

    Notes:
    - This provides a FastAPI-native simulation path independent of Flask agents.
    - You can later swap the logic for a physics-based solver while preserving the API contract.
    """
    from ..utils.simulation import simulate_table

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail={"error": "Invalid JSON body; expected an object."})

    context = body.get("context")
    op_params = body.get("op_params")
    if not isinstance(context, dict):
        raise HTTPException(status_code=400, detail={"error": "Field 'context' is required and must be an object."})
    if not isinstance(op_params, dict):
        raise HTTPException(status_code=400, detail={"error": "Field 'op_params' is required and must be an object."})

    result = simulate_table(context, op_params)
    if isinstance(result, tuple):  # (error_json, status)
        payload, status = result
        raise HTTPException(status_code=status, detail=payload)

    return result


@router.post("/calibrate_param")
async def post_model_calibration_parameter(_: Request, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    # Placeholder until query_cal_param logic is ported
    raise HTTPException(status_code=501, detail=_not_implemented("Calibration parameter discovery (/api/calibration/calibrate_param)"))


@router.post("/calibrate")
async def post_model_calibrate(_: Request, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    # Placeholder until ModelCalibrationAgent is ported
    raise HTTPException(status_code=501, detail=_not_implemented("Calibration (/api/calibration/calibrate)"))
