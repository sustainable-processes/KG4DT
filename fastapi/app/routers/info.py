from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Body

from ..services.graphdb import GraphDBClient
from ..utils import graphdb_exploration_utils as gxu
from ..schemas.exploration import InfoContext

router = APIRouter(prefix="/api/model", tags=["info"])  # keep base aligned with Flask




@router.post("/info")
async def post_model_info(request: Request, body: InfoContext = Body(..., description="Context object for info aggregation")):
    """Return model/ontology information using a provided JSON context.

    Use this POST endpoint from Swagger UI to include a request body.
    """
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    context: Dict[str, Any] = {}
    if isinstance(body, InfoContext) and isinstance(body.context, dict):
        context = body.context

    try:
        data = gxu.query_info(client, context)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Failed to assemble model info", "detail": str(e)})
