from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..services.graphdb import GraphDBClient
from ..utils import graphdb_exploration_utils as gxu

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


@router.get("/pheno/param_law")
async def get_param_law(request: Request):
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    # Read JSON body if provided (FastAPI allows body for GET but needs explicit usage via Request)
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        body = {}

    desc: Dict[str, Any] = {}
    keys = ("ac", "fp", "mt", "me")
    for k in keys:
        val = body.get(k) if isinstance(body, dict) else None
        if val is None:
            # also from query params
            qvals = request.query_params.getlist(k)
            if qvals:
                val = qvals
            else:
                single = request.query_params.get(k)
                if single:
                    val = [p.strip() for p in single.split(",") if p.strip()]
        if val is not None:
            desc[k] = val

    if not any(desc.get(k) for k in keys):
        raise HTTPException(status_code=400, detail={
            "error": "Provide at least one of 'ac', 'fp', 'mt', or 'me' via JSON body or query params.",
            "hint": {"GET": "/api/model/pheno/param_law?fp=Annular_Microflow&mt=Engulfment"}
        })

    data = gxu.query_param_law(client, desc)
    if isinstance(data, dict) and data.get("error") == "NotImplemented":
        raise HTTPException(status_code=501, detail=data)
    return data


@router.get("/pheno/rxn")
async def get_rxn(request: Request):
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    # Filters are only allowed in the JSON body, not query params, to match Flask behavior
    forbidden_keys = [
        "ac", "accumulation",
        "fp", "flow_pattern",
        "mt", "mass_transport",
        "me", "mass_equilibrium",
        "param", "parameter",
        "law", "law_name", "laws",
        "param_law",
    ]
    forbidden_in_args = {k: request.query_params.getlist(k) for k in forbidden_keys if request.query_params.getlist(k)}
    if forbidden_in_args:
        raise HTTPException(status_code=400, detail={
            "error": "Pass filters in the request JSON body. Query parameters are not supported for this endpoint.",
            "forbidden_query_params": forbidden_in_args,
        })

    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        body = {}

    def _collect_list(primary: str, aliases: Optional[List[str]] = None) -> List[str]:
        aliases = aliases or []
        val = body.get(primary) if isinstance(body, dict) else None
        if val is None:
            for a in aliases:
                if isinstance(body, dict) and a in body:
                    val = body.get(a)
                    break
        if val is None:
            return []
        if isinstance(val, list):
            return [str(x).strip() for x in val if x is not None and str(x).strip() != ""]
        return [str(val).strip()] if str(val).strip() != "" else []

    filters: Dict[str, Any] = {}
    ac_list = _collect_list("ac", ["accumulation"])  # Batch / Continuous
    fp_list = _collect_list("fp", ["flow_pattern"])  # Flow pattern
    mt_list = _collect_list("mt", ["mass_transport"])  # Mass transport phenomenon
    me_list = _collect_list("me", ["mass_equilibrium"])  # Mass equilibrium phenomenon
    param_list = _collect_list("param", ["parameter"])  # Variables used in laws
    law_list = _collect_list("law", ["law_name", "laws"])  # Law names

    if ac_list:
        filters["ac"] = ac_list
    if fp_list:
        filters["fp"] = fp_list
    if mt_list:
        filters["mt"] = mt_list
    if me_list:
        filters["me"] = me_list
    if param_list:
        filters["param"] = param_list
    if law_list:
        filters["law"] = law_list

    if isinstance(body, dict) and "param_law" in body and body.get("param_law") is not None:
        filters["param_law"] = body.get("param_law")

    if not filters:
        data = gxu.query_rxn(client, None)
    else:
        data = gxu.query_rxn(client, filters)

    if isinstance(data, dict) and data.get("error") == "NotImplemented":
        raise HTTPException(status_code=501, detail=data)
    if not data:
        raise HTTPException(status_code=404, detail={"error": "No reaction phenomenon matched the provided filters.", "filters": filters})
    return data
