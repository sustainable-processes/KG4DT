Models API (FastAPI)

This document explains how to edit and query the SQL models exposed by the FastAPI backend. All endpoints are available in the interactive Swagger UI at:

- http://localhost:8001/docs
- http://localhost:8001/redoc

Authentication: Not enabled by default. In production, protect these endpoints accordingly (authN/Z, rate limiting).

Base path
- All model endpoints are prefixed with /models.

Entities and endpoints

1) Basic
- List: GET /models/basics?limit=100&offset=0
- Get: GET /models/basics/{id}
- Create: POST /models/basics
- Update: PATCH /models/basics/{id}
- Delete: DELETE /models/basics/{id}

Example payload (create)
{
  "name": "Exp-1",
  "size": 1.5,
  "substance": "H2O",
  "time": 120.0,
  "pressure": 1.0,
  "temperature": 25.0,
  "structure": {"nodes": [], "edges": []}
}

2) Project
- List: GET /models/projects?limit=100&offset=0&user_id=123
- Get: GET /models/projects/{id}
- Create: POST /models/projects
- Update: PATCH /models/projects/{id}
- Delete: DELETE /models/projects/{id}

Example payload (create)
{
  "name": "Project A",
  "user_id": 1,
  "model": "Well_Mixed",
  "content": {"parameters": {"k": 0.1}}
}

3) Reactor
- List: GET /models/reactors?limit=100&offset=0
- Get: GET /models/reactors/{id}
- Create: POST /models/reactors
- Update: PATCH /models/reactors/{id}
- Delete: DELETE /models/reactors/{id}

Example payload (create)
{
  "name": "CSTR",
  "number_of_input": 2,
  "number_of_utility_input": 1,
  "icon": "cstr.svg",
  "json_data": {"notes": "free-form structure"},
  "chemistry": {"species": ["A", "B"], "reactions": ["A+B->C"]},
  "phenomenon": {"ac": "Batch", "fp": "Well_Mixed"}
}

4) Template
- List: GET /models/templates?limit=100&offset=0
- Get: GET /models/templates/{id}
- Create: POST /models/templates
- Update: PATCH /models/templates/{id}
- Delete: DELETE /models/templates/{id}

Example payload (create)
{
  "category": "Well_Mixed_Default",
  "reactor_id": 1
}

5) Assembly Templates (grouped view)
- Get grouped templates with embedded reactor data: GET /models/assembly_templates

Response shape
{
  "<Category>": [
    {
      "name": "<reactor name>",
      "icon": "<icon file>",
      "created_date": "<ISO timestamp>",
      "number_of_input": <int>,
      "number_of_utility_input": <int>,
      "chemistry": {},
      "phenomenon": {},
      "input": { ... },
      "utility": { ... },
      "reactor": { ... }
    }
  ]
}

Notes
- The sections input/utility/reactor are taken from Reactor.json_data if present.
- Categories correspond to Template.category values (e.g., "Template", "Tutorial").

Example
curl "http://localhost:8001/models/assembly_templates"

5) SpeciesRole
- List: GET /models/species-roles?limit=100&offset=0&order_by=id&order_dir=asc
- Get: GET /models/species-roles/{id}
- Create: POST /models/species-roles
- Update: PATCH /models/species-roles/{id}
- Delete: DELETE /models/species-roles/{id}

Example payload (create)
{
  "name": "Catalyst",
  "attribute": "Pt/C"
}

Usage examples (curl)

- Create a Project
curl -X POST http://localhost:8001/models/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"ProjA","user_id":1,"model":"Well_Mixed","content":{"p":[]}}'

- List Projects
curl "http://localhost:8001/models/projects?user_id=1&limit=50"

- Get a Reactor
curl http://localhost:8001/models/reactors/1

- Create a Template referencing a Reactor
curl -X POST http://localhost:8001/models/templates \
  -H "Content-Type: application/json" \
  -d '{"category":"Well_Mixed_Default","reactor_id":1}'

- Update a Basic (partial)
curl -X PATCH http://localhost:8001/models/basics/1 \
  -H "Content-Type: application/json" \
  -d '{"temperature":35.0}'

5) Ontology queries (GraphDB)
- Variables: GET /api/model/var
- Units: GET /api/model/unit

Examples
- curl http://localhost:8001/api/model/var
- curl http://localhost:8001/api/model/unit

6) Assembly (knowledge graph)
- Species roles (from KG): GET /api/model/assembly/list_species_role?limit=100&offset=0&order_dir=asc|desc
  - Returns: {"species_roles": ["Catalyst","Reactant",...], "count": N, "source": "kg"}
  - Example:
    curl "http://localhost:8001/api/model/assembly/list_species_role?limit=50&order_dir=asc"

Notes
- All PATCH updates are partial; only provided fields are changed.
- Pagination: limit is capped at 500; offset >= 0.
- JSON fields (content, json_data, chemistry, phenomenon, structure) accept arbitrary objects; keep payload small.
- Timestamps are server-generated where applicable (Project.datetime, Project.last_update, Reactor.created_date).
- Error responses follow standard HTTP codes (404 when not found, 400 for validation issues).
