Exploration API (FastAPI)

These endpoints mirror the Flask router_exploration_api.py routes and interact with the knowledge graph (GraphDB).

Base path
- /api/model

Endpoints
- GET /api/model/pheno
  - Status: Not yet implemented in FastAPI (returns 501).
  - Intended to return a dictionary aggregating dimensions, laws, variables, units, and phenomena.

- GET /api/model/pheno/ac
  - Returns a sorted list of Accumulation categories (e.g., ["Batch", "Continuous"]).
  - Example:
    curl http://localhost:8001/api/model/pheno/ac

- GET /api/model/pheno/fp?ac=Batch|Continuous|CSTR
  - Status: Not yet implemented in FastAPI (returns 501 for now).
  - Will return flow patterns for a given accumulation method.

- GET /api/model/pheno/mt?fp=<FlowPattern>
  - Status: Not yet implemented in FastAPI (returns 501 for now).
  - Will return mass transport phenomena for a given flow pattern.

- GET /api/model/pheno/me?mt=<MT>&mt=<MT2>
  - Status: Not yet implemented in FastAPI (returns 501 for now).
  - Will return mass equilibrium phenomena for one or more mass transport phenomena.

- GET /api/model/pheno/param_law
  - Status: Not yet implemented in FastAPI (returns 501 for now).
  - Accepts filters in body or query params: ac, fp, mt, me.

- GET /api/model/pheno/rxn
  - Status: Not yet implemented in FastAPI (returns 501 for now).
  - Accepts filters only in the JSON body (not query), matching Flask behavior.

Configuration
- Ensure GraphDB is reachable and repository is configured in fastapi/.env:
  FASTAPI_GRAPHDB_BASE_URL=http://localhost:7200
  FASTAPI_GRAPHDB_REPOSITORY=ontomo
  FASTAPI_GRAPHDB_USERNAME=admin    # optional
  FASTAPI_GRAPHDB_PASSWORD=root     # optional
  FASTAPI_GRAPHDB_TIMEOUT_SECONDS=15

Implementation notes
- Service: fastapi/app/services/graphdb.py provides GraphDBClient (SPARQLWrapper-based).
- Utils: fastapi/app/utils/graphdb_exploration_utils.py contains SPARQL helpers used by this router.
- Router: fastapi/app/routers/exploration.py wires HTTP endpoints to utils and applies validations.

Extending the implementation
- Port SPARQL logic from Flask (backend/utils/phenomenon_service.py and graphdb_handler.py) into the utils module.
- Replace NotImplemented returns with actual SPARQL queries using client.select(query) and transform results.
- Keep outputs consistent with Flask to allow frontend reuse.

Run
- uvicorn fastapi.app.main:app --reload --port 8001
- Explore docs at http://localhost:8001/docs
