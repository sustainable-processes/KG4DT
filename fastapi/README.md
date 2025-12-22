KG4DT FastAPI Backend

Overview & Intention
- This folder contains a modern FastAPI backend designed to reach and exceed feature parity with the legacy Flask backend (in `backend/`).
- **Intention**: The goal is to provide a robust, high-performance API that leverages Python's type hints for better developer experience, automatic documentation (OpenAPI/Swagger), and improved security. It serves as the primary interface for both Knowledge Graph exploration and relational data management.
- The code is structured with security, maintainability, and clean architecture principles at its core.

Developer Attributes & Principles
- **Security-First by Default**
  - **Least Privilege**: Ownership is strictly verified for all sensitive resources (Projects, Models, Experiment Data). Users must provide their identifier (email) to access or modify their data.
  - **Input Validation**: All inputs are validated and sanitized using Pydantic schemas; never trust client data.
  - **Secure Defaults**: CORS is restrictive by default and configurable via environment variables.
- **Backend Engineering Best Practices**
  - **Generic Update Patterns**: Standardized `PATCH` operations using helper utilities to reduce boilerplate and ensure consistent behavior across all resources.
  - **Decoupled Validation**: Business logic constraints (like uniqueness checks) are separated from the data persistence layer, making the code more modular and testable.
  - **DRY Routing**: API prefixes and versioning are managed centrally in `main.py`, allowing routers to remain "clean" and focused only on logic.
  - **Consistent Error Handling**: Structured HTTP exceptions provide clear feedback to the frontend while preventing internal detail leaks.
- **Object-Oriented Programming (OOP)**
  - Encapsulate infra/business logic in services (e.g., `GraphDBClient`) for testability and reuse.
  - Favor composition over inheritance and keep units of code small and cohesive.

Project Layout
- `app/`
  - `main.py`: Application entry point, dynamic router inclusion, and CORS configuration.
  - `settings.py`: Pydantic-based configuration (single source of truth for env vars).
  - `dependencies.py`: Request-scoped dependencies (e.g., DB session).
  - `db/`: Database initialization, engine setup, and idempotent startup migrations.
  - `models/`: SQLAlchemy ORM models (v1 relational schema).
  - `schemas/`: Pydantic models for request validation and response serialization.
  - `services/`: External service clients (e.g., GraphDB SPARQL client).
  - `routers/`: Resource-specific API endpoints (Assembly, Exploration, Calibration, etc.).
  - `utils/`: 
    - `db.py`: Shared database utilities (ownership verification, generic updates).
    - `graphdb_*.py`: SPARQL helpers for specific domain logic.
- `requirements.txt`: Python dependencies.

API Architecture & Routing
The API is designed to be resource-centric and intuitive. All endpoints are available under both `/api/` (latest) and `/api/v1/` prefixes.

1. **Assembly (`/api/assembly`)**
   - Manages the structural components of models.
   - Sub-groups: `/projects`, `/reactors`, `/templates`, `/species_roles`.
2. **Exploration (`/api/exploration`)**
   - Knowledge Graph-backed discovery of phenomena (Accumulation, Flow Patterns, Mass Transfer, etc.).
3. **Calibration (`/api/calibration`)**
   - Handles law metadata, symbol resolution, and parameter derivation (OpParams).
4. **Knowledge Graph & Translation (`/api/v1/kg_components`, `/api/assembly/kg_components`, `/api/v1/translate_frontend_json`)**
   - **KG Components**: Directly translates Knowledge Graph individuals (like Reactors) into frontend structures. Available at `/api/v1/kg_components` and `/api/assembly/kg_components`.
   - **Frontend Translation**: Standardizes the conversion of frontend JSON payloads into the `context` format required by backend agents (Simulation/Calibration).

Quick Start
1) Install dependencies (prefer a virtualenv or Conda environment)
   ```bash
   pip install -r fastapi/requirements.txt
   ```

2) Configure environment variables
   Create a `fastapi/.env` file (see "Environment configuration" below).

3) Run the development server
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

Health Checks
- `GET /health` → `{"status": "ok"}`
- `GET /health/deep` → `{ "status": "ok", "database": true, "graphdb": true }`

Future Steps
- Complete the migration of complex simulation and calibration agents from Flask.
- Implement full Role-Based Access Control (RBAC) and JWT authentication.
- Expand unit and integration test coverage for all domain utilities.
- Implement request IDs and structured logging for better production observability.

Environment Configuration (.env)
- **Location**: Place the file at `fastapi/.env`.
- **Prefix**: All variables must be prefixed with `FASTAPI_` to avoid collisions.
- **Recommended Keys**:
  ```ini
  FASTAPI_APP_NAME=KG4DT FastAPI
  FASTAPI_DEBUG=false
  FASTAPI_DATABASE_URL=postgresql://user:pass@localhost:5432/kg4dt
  FASTAPI_GRAPHDB_BASE_URL=http://localhost:7200
  FASTAPI_GRAPHDB_REPOSITORY=kg4dt
  ```

Shared Logic & Utilities
- **Ownership Helper**: `verify_project_ownership` ensures that the requesting user (via email) has permissions for the resource.
- **Update Helper**: `apply_updates` provides a safe way to apply partial updates from `PATCH` requests to SQLAlchemy models.
- **Uniqueness Helper**: `validate_uniqueness` standardizes how we check for conflicting records before creation or renaming.

Translation Engine logic
- **Frontend → Backend Context**:
  - Purpose: Convert UI-specific JSON (Chemistry, Inputs, Phenomena) into a standardized `context` for simulation/calibration.
  - Implementation: `fastapi/app/utils/frontend_translation.py` maps top-level species/reactions to `basic.spc`/`basic.rxn`, and input-level phases to `stm`/`sld`/`gas`. It also populates the `desc` section from phenomena selections.
- **Knowledge Graph → Frontend**:
  - Purpose: Pre-fill frontend forms with descriptors and parameters derived from KG individuals.
  - Implementation: `fastapi/app/utils/kg_translation.py` queries KG context templates and translates state/operating parameters into UI-compatible placeholders (Values or Ranges).

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
