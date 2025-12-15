KG4DT FastAPI Backend

Overview
- This folder contains a new FastAPI backend that will gradually reach feature parity with the existing Flask backend (in backend/). 
- The code here is structured with security, maintainability, and object‑oriented design in mind.

Developer attributes & principles
- Security-first by default
  - Validate and sanitize inputs; never trust client data.
  - Principle of least privilege (scoped DB permissions, minimal network access).
  - Do not log secrets or sensitive user data. Use structured logs and redaction.
  - CORS is restrictive by default and configurable via environment variables.
  - Timeouts, retries, and defensive error handling for external calls (e.g., GraphDB).
- Best practices for backend engineering
  - Twelve-Factor App: configuration via environment variables; no hard-coded credentials.
  - Clear boundaries: routers (API), services (business/infra logic), dependencies (DI), settings (config).
  - Consistent error handling and typed interfaces for maintainability.
  - Observability hooks (health checks) to aid deployment and ops.
- Object-Oriented Programming (OOP)
  - Encapsulate infra/business logic in classes (e.g., GraphDBClient) for testability and reuse.
  - Favor composition over inheritance; keep classes small and cohesive.
  - Write interfaces that allow mocking in tests.

Project layout (under this folder)
- app/
  - main.py: FastAPI application creation, CORS, startup initialization.
  - settings.py: Pydantic-based configuration (env-driven).
  - dependencies.py: Request-scoped dependencies (e.g., DB session).
  - services/
    - graphdb.py: GraphDB SPARQL client (minimal wrapper).
  - routers/
    - health.py: Health endpoints (basic and deep checks).
    - model.py: Ontology variable/unit endpoints (GraphDB-backed).
    - exploration.py: Phenomena exploration endpoints (ac/fp/mt/me, param_law, rxn).
    - calibration.py: Law/symbol/triplets, op_param, simulate (and placeholders for cal_param/calibrate).
    - info.py: Aggregated info endpoint.
  - utils/
    - graphdb_model_utils.py: SPARQL helpers for variables/units.
    - graphdb_exploration_utils.py: SPARQL helpers for phenomena queries.
    - graphdb_calibration_utils.py: Law metadata, op_param derivation, triplets.
    - simulation.py: Lightweight table simulation helper.
- requirements.txt: Python dependencies for this FastAPI service.

Quick start
1) Install dependencies (prefer a virtualenv or Conda environment)
   pip install -r fastapi/requirements.txt

2) Configure environment variables
   Database (FastAPI has its own DB config, independent of Flask):
   - FASTAPI_DATABASE_URL
     or all of the following:
   - FASTAPI_DB_HOST (default: localhost)
   - FASTAPI_DB_PORT (default: 5432)
   - FASTAPI_DB_USER (default: postgres)
   - FASTAPI_DB_PASSWORD (default: postgres)
   - FASTAPI_DB_NAME (no default; required if FASTAPI_DATABASE_URL is not set)

   GraphDB (SPARQL endpoint) for this FastAPI service (prefixed with FASTAPI_):
   - FASTAPI_GRAPHDB_BASE_URL (default: http://localhost:7200)
   - FASTAPI_GRAPHDB_REPOSITORY (default: kg4dt)
   - FASTAPI_GRAPHDB_USERNAME (optional)
   - FASTAPI_GRAPHDB_PASSWORD (optional)
   - FASTAPI_GRAPHDB_TIMEOUT_SECONDS (default: 15)

   Optional:
   - FASTAPI_APP_NAME (default: KG4DT FastAPI)
   - FASTAPI_DEBUG (default: false)
   - FASTAPI_CORS_ORIGINS (JSON array or comma-separated list not supported directly; prefer default or override in code if needed)
   - FASTAPI_DATABASE_ECHO (default: false)

3) Run the development server from the repository root
   uvicorn app.main:app --reload --port 8001

   Notes:
   - The FastAPI backend maintains its own SQLAlchemy models (fastapi/app/models) and engine/session setup (fastapi/app/db). They are initialized on startup independently of the Flask backend.
   - The service exposes a basic health endpoint at /health and a deep health check at /health/deep.

Health checks
- GET /health → {"status": "ok"}
- GET /health/deep → { "status": "ok" | "degraded", "database": bool, "graphdb": bool }

Future steps (out of scope for this commit)
- Gradually port Flask endpoints (router_*.py) into FastAPI routers.
- Add authentication/authorization middleware and RBAC.
- Add validation schemas (Pydantic models) for request/response payloads.
- Implement rate limiting, request IDs, and structured logging.
- Add unit/integration tests and CI.


Environment configuration (.env)
- Location: Place the FastAPI service env file at fastapi/.env. The app automatically loads this file on startup regardless of where you run uvicorn from.
- Prefix: All variables for this FastAPI backend should be prefixed with FASTAPI_ to avoid collisions with the Flask app.
- Recommended keys (copy to fastapi/.env):

  FASTAPI_APP_NAME=KG4DT FastAPI
  FASTAPI_DEBUG=false
  # Database (choose either FASTAPI_DATABASE_URL or the individual parts below)
  FASTAPI_DATABASE_URL=postgresql://postgres:password@localhost:5432/kg4dt
  # or
  FASTAPI_DB_HOST=localhost
  FASTAPI_DB_PORT=5432
  FASTAPI_DB_USER=postgres
  FASTAPI_DB_PASSWORD=postgres
  FASTAPI_DB_NAME=kg4dt

  # GraphDB
  FASTAPI_GRAPHDB_BASE_URL=http://localhost:7200
  FASTAPI_GRAPHDB_REPOSITORY=kg4dt
  # Optional auth
  # FASTAPI_GRAPHDB_USERNAME=admin
  # FASTAPI_GRAPHDB_PASSWORD=secret
  FASTAPI_GRAPHDB_TIMEOUT_SECONDS=15

- Note: Legacy keys like GRAPHDB_HOST/PORT/DB without the FASTAPI_ prefix will be ignored by the FastAPI service. Keep Flask-specific variables in backend/.env if needed.
- Security: Do not commit real secrets. Prefer creating fastapi/.env from a template like fastapi/.env.example and adding fastapi/.env to .gitignore.


Single-source configuration (best practice)
- The FastAPI service now uses a single configuration source: fastapi/app/settings.py.
- Use get_settings() from that module to access configuration throughout the code. Avoid using os.getenv() or calling load_dotenv() in modules.
- Benefits: consistent env loading from fastapi/.env, type validation, testability, and no duplicated config logic.

Example usage
- from fastapi.app.settings import get_settings
- settings = get_settings()
- db_url = settings.database_url  # or build parts from settings.db_host, settings.db_port, etc.

Database initialization
- The DB initializer fastapi.app.db.init_db accepts settings and echo:
  init_db(echo=settings.database_echo, settings=settings)
- This ensures all env resolution flows through one place (Settings), avoiding surprises with os.getenv.

Operation parameters (op_param) — logic overview
- Purpose: determine which OperationParameter variables are needed in a model context and their indexing (global, per-stream, per-gas, per-solid, per-species-in-<index>).
- Inputs (context):
  - basic: lists/index maps for streams (stm), gases (gas), solids (sld), and their species memberships.
  - desc: selected phenomena (ac/fp/mt/me), optional reaction-to-phenomena map (rxn), and parameter-to-law map (param_law).
- Algorithm (high level):
  - Query GraphDB for laws and variables; build sets of variables tied to selected phenomena (accumulation, flow pattern, mass transfer, mass equilibrium).
  - Include variables from associated gas/solid laws when selected MTs imply them and basic context declares gases/solids.
  - Include variables referenced via reaction→phenomenon relationships and variables of laws those variables participate in.
  - Filter for variables that are OperationParameter and have no own laws (pure inputs), then expand by their dimensions to indices:
    - [] → global OP: [name, null, null, null, null]
    - [Stream] → for each stream: [name, null, stream, null, null]
    - [Gas] → for each gas: [name, gas, null, null, null]
    - [Solid] → for each solid: [name, solid, null, null, null]
    - [Species, Stream] → for each stream×species-in-stream: [name, null, stream, null, species]
    - [Species, Gas] → for each gas×species-in-gas: [name, gas, null, null, species]
    - [Species, Solid] → for each solid×species-in-solid: [name, solid, null, null, species]
- Output: deterministic, sorted list of [name, idx1, idx2, idx3, idx4].
- File: fastapi/app/utils/graphdb_calibration_utils.py (query_op_param and helpers). Use via POST /api/model/op_param.

Simulation — logic overview
- Endpoint: POST /api/model/simulate
- Inputs: JSON body with 'context' and 'op_params' (dataset object with 'ind' and 'val').
- Behavior: a lightweight, deterministic computation that returns one simulated scalar per experiment row by summing numeric cells in that row. Non-numeric cells are ignored. This provides a stable API surface while decoupled from Flask agents.
- Output: { "simulated": { "ind": same-as-op_params.ind, "val": [[y1], ...] }, "count": N }
- Extensibility: replace fastapi/app/utils/simulation.py:simulate_table with a physics-based solver that uses the 'context' and GraphDB-derived model structure. Keep the input/output contract for backward compatibility.
- Security: request validation ensures shapes; no code execution from inputs; numerical operations only.
