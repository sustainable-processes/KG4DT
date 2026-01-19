Exploration API (FastAPI)

These endpoints mirror the Flask router_exploration_api.py routes and interact with the knowledge graph (GraphDB).

Base path
- /api/exploration
- /api/v1/exploration

Endpoints
- GET /api/exploration/pheno
  - Returns a dictionary of phenomena and their relations (cls, fps, mts, mes). Example:
    curl http://localhost:8001/api/exploration/pheno

- GET /api/exploration/pheno/ac
  - Returns a sorted list of Accumulation categories (e.g., ["Batch", "Continuous"]).
  - Example:
    curl http://localhost:8001/api/exploration/pheno/ac

- GET /api/exploration/pheno/fp?ac=Batch|Continuous|CSTR
  - Returns flow patterns for a given accumulation method (case-insensitive).
  - Example:
    curl "http://localhost:8001/api/exploration/pheno/fp?ac=Batch"

- GET /api/exploration/pheno/mt?fp=<FlowPattern>
  - Returns mass transport phenomena for a given flow pattern.
  - Example:
    curl "http://localhost:8001/api/exploration/pheno/mt?fp=Well_Mixed"

- GET /api/exploration/pheno/me?mt=<MT>&mt=<MT2>
  - Returns mass equilibrium phenomena for one or more mass transport phenomena.
  - Example:
    curl "http://localhost:8001/api/exploration/pheno/me?mt=Engulfment&mt=Interfacial_Turbulence"

- POST /api/exploration/pheno/param_law
  - Provide filters in the JSON body using any of keys: ac, fp, mt, me (string or list).
  - Example:
    curl -X POST http://localhost:8001/api/exploration/pheno/param_law \
      -H "Content-Type: application/json" \
      -d '{"ac":"Batch","fp":"Well_Mixed","mt":["Mass-Controlled_Gas-Liquid_Mass_Transfer","Solid-Liquid_Mass_Transfer"],"me":["Mass-Controlled_Gas_Dissolution_Equilibrium","Solid_Dissolution_Equilibrium"]}'

- GET /api/exploration/pheno/rxn
  - Returns all ReactionPhenomenon names from the knowledge graph. No parameters or body required.
  - Example:
    curl http://localhost:8001/api/exploration/pheno/rxn


- POST /api/exploration/info
  - Returns a minimal information block combining phenomena and reaction names.
  - Send an optional JSON context object in the body.
  - Example:
    curl -X POST http://localhost:8001/api/exploration/info -H "Content-Type: application/json" -d '{"context": {}}'

- POST /api/exploration/experiment_data/upload
  - Upload a CSV file and save its content as ExperimentData.
  - The CSV is parsed into JSON and stored in the database.
  - Form fields: `project_id` (int), `model_id` (int), `file` (CSV file).
  - Query parameter: `email` (string) for ownership verification.
  - Example:
    ```bash
    curl -X POST "http://localhost:8001/api/exploration/experiment_data/upload?email=user@example.com" \
      -F "project_id=1" \
      -F "model_id=2" \
      -F "file=@data.csv"
    ```

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
