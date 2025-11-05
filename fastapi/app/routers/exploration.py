from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Body

from ..services.graphdb import GraphDBClient
from ..utils import graphdb_exploration_utils as gxu
from ..schemas.exploration import ParamLawFilters, RxnFilters

router = APIRouter(prefix="/api/model", tags=["exploration"])  # keep paths aligned with Flask


@router.get("/pheno")
async def get_pheno(request: Request):
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")
    data = gxu.query_pheno(client)
    if isinstance(data, dict) and data.get("error") == "NotImplemented":
        raise HTTPException(status_code=501, detail=data)
    return data


@router.get("/pheno/ac")
async def get_pheno_ac(request: Request) -> List[str]:
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")
    return gxu.query_ac(client)


@router.get("/pheno/fp")
async def get_pheno_fp(ac: str = Query(..., description="Accumulation type: Batch, Continuous, or CSTR"), request: Request = None):
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    if ac is None or str(ac).strip() == "":
        raise HTTPException(status_code=400, detail="Missing required query parameter 'ac'. Allowed values: 'Batch', 'Continuous', 'CSTR'.")
    ac_norm = str(ac).strip().lower()
    allowed = {"batch", "continuous", "cstr"}
    if ac_norm not in allowed:
        raise HTTPException(status_code=400, detail={"error": "Invalid value for 'ac'. Allowed values are 'Batch', 'Continuous', or 'CSTR'.", "received": ac})

    data = gxu.query_fp_by_ac(client, ac_norm)
    if isinstance(data, dict) and data.get("error") == "NotImplemented":
        raise HTTPException(status_code=501, detail=data)
    if data is None or (isinstance(data, (list, dict)) and len(data) == 0):
        raise HTTPException(status_code=404, detail={"error": "No phenomenon found for the specified operating condition.", "method": ac})
    return data


@router.get("/pheno/mt")
async def get_pheno_mt(fp: str = Query(..., description="Flow pattern name"), request: Request = None):
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    if fp is None or str(fp).strip() == "":
        raise HTTPException(status_code=400, detail={"error": "Missing required query parameter 'fp' (flow pattern).", "hint": "Example: /api/model/pheno/mt?fp=Annular_Microflow"})

    data = gxu.query_mt_by_fp(client, fp)
    if isinstance(data, dict) and data.get("error") == "NotImplemented":
        raise HTTPException(status_code=501, detail=data)
    if data is None or (isinstance(data, (list, dict)) and len(data) == 0):
        raise HTTPException(status_code=404, detail={"error": "No mass transfer phenomenon found for the specified flow pattern.", "pattern": fp})
    return data


@router.get("/pheno/me")
async def get_pheno_me(request: Request, mt: Optional[List[str]] = Query(None, description="Mass transport names; may be provided multiple times or comma-separated")):
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    # Normalize mt list similar to Flask implementation
    mt_list: List[str] = []
    if mt:
        for item in mt:
            if "," in item:
                mt_list.extend([p.strip() for p in item.split(",") if p.strip()])
            else:
                if item and str(item).strip():
                    mt_list.append(str(item).strip())

    if not mt_list:
        raise HTTPException(status_code=400, detail={
            "error": "Provide one or more 'mt' (mass transport) names via query params.",
            "hint": {"GET": "/api/model/pheno/me?mt=Engulfment"}
        })

    # Delegate and aggregate like Flask if the utility returns a list; otherwise handle NotImplemented
    # Since our utils currently returns NotImplemented, return that as 501.
    probe = gxu.query_me_by_mt(client, mt_list[0])
    if isinstance(probe, dict) and probe.get("error") == "NotImplemented":
        raise HTTPException(status_code=501, detail=probe)

    mes: set[str] = set()
    for item in mt_list:
        res = gxu.query_me_by_mt(client, item)
        if isinstance(res, list):
            for me in res:
                if me:
                    mes.add(str(me))
    if not mes:
        raise HTTPException(status_code=404, detail={"error": "No mass equilibrium found for the specified mass transport phenomena.", "mt": mt_list})
    return {"me": sorted(mes)}


def _build_param_law_desc(filters_model: ParamLawFilters | None) -> Dict[str, Any]:
    body: Dict[str, Any] = filters_model.model_dump(exclude_none=True) if isinstance(filters_model, ParamLawFilters) else {}
    desc: Dict[str, Any] = {}
    for k in ("ac", "fp", "mt", "me"):
        if k in body and body[k] is not None:
            desc[k] = body[k]
    return desc




@router.post("/pheno/param_law")
async def post_param_law(request: Request, filters: ParamLawFilters = Body(..., description="Phenomenon selections to constrain parameter-to-law mapping")):
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    # Reject query parameters for filters even on POST (body only)
    forbidden_keys = ["ac", "fp", "mt", "me"]
    forbidden_in_args = {k: request.query_params.getlist(k) for k in forbidden_keys if request.query_params.getlist(k)}
    if forbidden_in_args:
        raise HTTPException(status_code=400, detail={
            "error": "Provide filters in the JSON body only. Query parameters are not supported for this endpoint.",
            "forbidden_query_params": forbidden_in_args,
        })

    # Content-Type is enforced by FastAPI when Body(...) is present; additional manual check is optional.
    desc = _build_param_law_desc(filters)
    if not any(desc.get(k) for k in ("ac", "fp", "mt", "me")):
        raise HTTPException(status_code=400, detail={
            "error": "Provide at least one of 'ac', 'fp', 'mt', or 'me' in the JSON body.",
            "example": {"fp": "Annular_Microflow", "mt": ["Engulfment"]}
        })

    data = gxu.query_param_law(client, desc)
    return data




@router.get("/pheno/rxn")
async def get_rxn(request: Request):
    """Return ReactionPhenomenon names from the knowledge graph.

    This GET endpoint accepts no parameters or body and simply lists reactions
    discovered in GraphDB. Use the POST variant for filtered queries if needed.
    """
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    data = gxu.query_rxn(client)
    if isinstance(data, dict) and data.get("error") == "NotImplemented":
        raise HTTPException(status_code=501, detail=data)
    # Always return 200 with the list (possibly empty)
    return data


