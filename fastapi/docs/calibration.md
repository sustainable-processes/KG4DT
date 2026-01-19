Calibration and Knowledge Graph APIs (FastAPI)

Base path
- /api/calibration
- /api/v1/calibration

Summary
- This router ports selected endpoints from Flask router_calibration_api.py to FastAPI.
- Endpoints that require complex simulation/calibration agents are provided as POST-only with 501 Not Implemented until those agents are migrated.

Endpoints
1) GET /api/calibration/law
- Returns law metadata from GraphDB.
- Example:
  curl http://localhost:8001/api/calibration/law

2) POST /api/calibration/sym
- Resolve symbols for one or more Unit individuals.
- Body examples:
  {"unit": "Pa"}
  {"units": ["Pa", "m", "s"]}
- Example:
  curl -X POST http://localhost:8001/api/calibration/sym \
    -H "Content-Type: application/json" \
    -d '{"units":["Pa","m","s"]}'

3) GET /api/calibration/triplets
- Returns a minimal triplets representation built from variables and laws.
- Example:
  curl http://localhost:8001/api/calibration/triplets

4) POST /api/calibration/op_param
- Derive candidate operation parameters for the given modeling context. Send JSON in the body.
- Example:
  curl -X POST http://localhost:8001/api/calibration/op_param \
    -H "Content-Type: application/json" \
    -d '{
  "basic": {
    "spc": [
      "water","solvent","RDY","RYE","RYA","REA","RDEt","dimer","H2","cat2","cat-H","catX","catX-RDEt"
    ],
    "rxn": [
      "H2 + cat2 > 2 cat-H",
      "2 cat-H > H2 + cat2",
      "RDY + 2 cat-H > RYE + cat2",
      "RYE + 2 cat-H > RYA + cat2",
      "RYA + 2 cat-H > REA + cat2",
      "REA + 2 cat-H > RDEt + cat2",
      "RDEt + catX > catX-RDEt",
      "catX-RDEt > RDEt + catX",
      "RYE + catX-RDEt > dimer + catX",
      "REA + catX-RDEt > 2 H2 + dimer + catX"
    ],
    "stm": {"Batch stream": {"spc": ["water","solvent","cat2","catX"]}},
    "sld": {"RDY solid": {"spc": ["RDY"]}},
    "gas": {"Hydrogen gas": {"spc": ["H2"]}}
  },
  "desc": {
    "ac": "Batch",
    "fp": "Well_Mixed",
    "mt": ["Mass-Controlled_Gas-Liquid_Mass_Transfer","Solid-Liquid_Mass_Transfer"],
    "me": ["Mass-Controlled_Gas_Dissolution_Equilibrium","Solid_Dissolution_Equilibrium"],
    "param_law": {
      "Gas_Dissolution_Saturated_Concentration": "Gas_Dissolution_Saturated_Concentration_Law_with_Mass-Controlled_Gas_Dissolution_Equilibrium_by_Henry",
      "Solid_Dissolution_Saturated_Concentration": "Solid_Dissolution_Saturated_Concentration_Law_with_Solid_Dissolution_Equilibrium_over_Mass"
    },
    "rxn": {
      "H2 + cat2 > 2 cat-H": ["Plain_Rate_Constant", "Concentration_Power_Dependence"],
      "2 cat-H > H2 + cat2": ["Plain_Rate_Constant", "Concentration_Power_Dependence"],
      "RDY + 2 cat-H > RYE + cat2": ["Arrhenius_Referenced_to_293K", "Concentration_Power_Dependence"],
      "RYE + 2 cat-H > RYA + cat2": ["Plain_Rate_Constant", "Concentration_Power_Dependence"],
      "RYA + 2 cat-H > REA + cat2": ["Arrhenius_Referenced_to_293K", "Concentration_Power_Dependence"],
      "REA + 2 cat-H > RDEt + cat2": ["Plain_Rate_Constant", "Concentration_Power_Dependence"],
      "RDEt + catX > catX-RDEt": ["Plain_Rate_Constant", "Concentration_Power_Dependence"],
      "catX-RDEt > RDEt + catX": ["Plain_Rate_Constant", "Concentration_Power_Dependence"],
      "RYE + catX-RDEt > dimer + catX": ["Arrhenius_Referenced_to_293K", "Concentration_Power_Dependence"],
      "REA + catX-RDEt > 2 H2 + dimer + catX": ["Arrhenius_Referenced_to_293K", "Concentration_Power_Dependence"]
    }
  }
}'

5) POST /api/calibration/simulate
- Run a lightweight deterministic table simulation. Accepts JSON body with 'context' and 'op_params'.
- Input shape:
  {
    "context": {"desc": {"fp": "Well_Mixed"}},
    "op_params": {
      "ind": [["Stirring_Speed", null, null, null, null]],
      "val": [[300.0], [450.0], [600]]
    }
  }
- Output shape:
  {
    "simulated": {
      "ind": [["Stirring_Speed", null, null, null, null]],
      "val": [[300.0], [450.0], [600.0]]
    },
    "count": 3
  }
- Example:
  curl -X POST http://localhost:8001/api/calibration/simulate \
    -H "Content-Type: application/json" \
    -d '{
      "context": {"desc": {"fp": "Well_Mixed"}},
      "op_params": {"ind": [["Stirring_Speed", null, null, null, null]], "val": [[300],[450],[600]]}
    }'

6) POST /api/calibration/calibrate_param
- Placeholder (501). Expects JSON body. Depends on GraphDB query_cal_param migration.

7) POST /api/calibration/calibrate
- Placeholder (501). Expects JSON body. Depends on ModelCalibrationAgent migration.

8) POST /api/calibration/experiment_data/
- Create a new experiment data record.
- Body (JSON): `project_id` (int), `model_id` (int), `name` (string, optional), `data` (ExperimentDataContent object).
- `ExperimentDataContent` structure:
  ```json
  {
    "op_param": [ ["ParameterName", "Index1", "Index2", "Index3", "Index4"] ],
    "rows": [ ["Value1", "Value2"] ]
  }
  ```
- Query parameter: `email` (string) for ownership verification.
- Example:
  ```bash
  curl -X POST "http://localhost:8001/api/calibration/experiment_data/?email=user@example.com" \
    -H "Content-Type: application/json" \
    -d '{
      "project_id": 1,
      "model_id": 2,
      "name": "Exp 1",
      "data": {
        "op_param": [
          ["Experiment_No", null, null, null, null],
          ["Batch_Time", null, null, null, null]
        ],
        "rows": [
          [1, 152],
          [2, 311]
        ]
      }
    }'
  ```

9) POST /api/calibration/experiment_data/upload
- Upload a CSV file and save its content as ExperimentData.
- The CSV is parsed into the structured `ExperimentDataContent` format.
- Form fields: `project_id` (int), `model_id` (int), `name` (string, optional), `file` (CSV file).
- Query parameter: `email` (string) for ownership verification.
- Example:
  ```bash
  curl -X POST "http://localhost:8001/api/calibration/experiment_data/upload?email=user@example.com" \
    -F "project_id=1" \
    -F "model_id=2" \
    -F "name=Exp 1 Upload" \
    -F "file=@data.csv"
  ```

Configuration
- Ensure FASTAPI_GRAPHDB_* variables are set in fastapi/.env and GraphDB is running with the expected repository.

Notes
- For Swagger UI (/docs), use the POST endpoints when you need to send JSON bodies.
- The law, sym, and triplets endpoints are functional and backed by SPARQL queries via SPARQLWrapper.
