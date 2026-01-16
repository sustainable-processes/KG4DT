from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Body

from ..services.graphdb import GraphDBClient
from ..utils import graphdb_exploration_utils as gxu
from ..schemas.exploration import InfoContext

router = APIRouter(prefix="/api/model", tags=["info"])  # keep base aligned with Flask




@router.get("/info")
async def get_model_info(request: Request):
    """Return model/ontology information using default (empty) context.

    This matches the Flask behavior where GET /api/model/info is supported.
    """
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")
    try:
        data = gxu.query_info(client, {})
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Failed to assemble model info", "detail": str(e)})


@router.post("/info")
async def post_model_info(request: Request, body: InfoContext = Body(..., description="Context object for info aggregation")):
    """Return model/ontology information using a provided JSON context.

    Use this POST endpoint from Swagger UI to include a request body.
    """
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    context: Dict[str, Any] = {}
    if body.context and isinstance(body.context, dict):
        context = body.context
    else:
        # Use basic and desc directly if present
        if body.basic:
            context["basic"] = body.basic
        if body.desc:
            context["desc"] = body.desc

    try:
        data = gxu.query_info(client, context)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Failed to assemble model info", "detail": str(e)})
