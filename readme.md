# KG4DT
<p align="center">
<a href="https://en.wikipedia.org/wiki/Knowledge_graph">
        <img src="https://img.shields.io/badge/knowledge%20graph-red"></a>
<a href="https://en.wikipedia.org/wiki/Digital_twin">
        <img src="https://img.shields.io/badge/digital%20twin-red"></a>
<a href="https://en.wikipedia.org/wiki/Model#Physical_model">
        <img src="https://img.shields.io/badge/physical%20model-red"></a>
</p>

## Local Deployment
### GraphDB
[Download GraphDB Free Version](https://email.ontotext.com/e3t/Ctc/GD+113/cGJhF04/MW_yJT37MwtW6Y7wmj6bTsFDW3wqskQ5fYyv9N1HNy_43qgyTW95jsWP6lZ3q0VD3K397YPl19N3s8WmnlnGXWW7kVjn83DrmjDN3bMZmnmyTDDN84-mP-XghhSW8QRJK_3lnKqnW1kv7by4Zl7ZHW4BtV7k13XjDGMBmf6rd_KjVW44j5Rh8QcBKDW55dJ855hD0QjW8zGhHN98nlbjW5RVt872HmMX4W2z-z3w2kQgDSW8z7MhS4g5VFWW6c6Jdt7XN7HbW5dKdpK7sFScXW5rmxtb2cWHQXVqYYX21qkg7VW1RSGKz5v5CSvW5SgDKd7CjMStW3tyfCz1hslHLW5ck34P14gF61W5qYMT1162KtNW7GChRF17hyxSVYJDkh2zwfT-W22_RVn2jhWDbW8mdT878lMQR2W5KZmGK5nvCrYW8B1zp01GF7BgdHGSfK04)  
Put the downloaded zip file under the `graphdb/dist` folder.

### Docker
```
git clone https://github.com/sustainable-processes/KG4DT.git
cd KG4DT
docker-compose up
```
Find deployed KG4DT and example cases at http://127.0.0.1:5000/index

### Having trouble starting Docker Desktop?
If Docker Desktop fails to start with errors like:
- com.docker.virtualization: process terminated unexpectedly: use of closed network connection

See the troubleshooting guide:
- docs/TROUBLESHOOTING_DOCKER.md

You can also run KG4DT without Docker using a Python virtual environment; see the next section for instructions.

### Local setup with Python virtual environment (.venv)
If you prefer to run without Docker:

1. Clone the repository
   - `git clone https://github.com/sustainable-processes/KG4DT.git`
   - `cd KG4DT`
2. Create and activate a virtual environment
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
   - Windows (Powershell): `py -m venv .venv; .venv\Scripts\Activate.ps1`
3. Install dependencies
   - `pip install -r requirements.txt`
4. (Optional) Configure environment variables by creating a `.env` file in the project root. Defaults are shown in parentheses:
   - `FLASK_DEBUG=True` (False)
   - `GRAPHDB_HOST=127.0.0.1`
   - `GRAPHDB_PORT=7200`
   - `GRAPHDB_USER=admin`
   - `GRAPHDB_PASSWORD=root`
   - `GRAPHDB_DB=ontomo`
   - `APP_PREFIX=` (leave empty for default)
5. Run the application
   - `python run.py`
   - The app starts at http://127.0.0.1:5000/

Note: The backend expects a running GraphDB instance with the specified credentials. See GraphDB section above.

## API Reference
Base URL: `http://127.0.0.1:5000`

- For a complete, up-to-date list of FastAPI endpoints and examples, see fastapi/docs/api.md

Notes:
- JSON request bodies should be sent with `Content-Type: application/json`.
- Some routes are marked as deprecated in code comments but are currently available; treat them as subject to change.

### Quick links
- Variables: GET `/api/model/var`
- Units: GET `/api/model/unit`
- Model info: POST `/api/model/info`
- Phenomena: see `/api/model/pheno*` (details in fastapi/docs/api.md)
- Operation parameters: POST `/api/model/op_param`
- Simulation: POST `/api/model/simulate`

Additional legacy Flask endpoints (structure, application, knowledge_graph, solvent) may still be available in the Flask app paths and are documented below for reference, but the FastAPI layer is preferred going forward.

### Knowledge Graph (legacy Flask)
- GET `/api/knowledge_graph/mainpage`
  - Returns entity data for knowledge graph main page.
  - Example: `curl http://127.0.0.1:5000/api/knowledge_graph/mainpage`

- GET `/api/knowledge_graph/sidebar` (deprecated)
  - Computes knowledge graph data from sidebar entity.
  
- GET `/api/knowledge_graph/context/<case>`
  - Loads `top_down_rule_model_context.json` for the given case directory.
  - 404 if missing.
  - Example: `curl http://127.0.0.1:5000/api/knowledge_graph/context/esterification`

- POST `/api/knowledge_graph/context`
  - Body (JSON): `{ "case": "esterification", "postfix": "top_down_rule_model_context.json" | "<suffix>" }`
  - If `postfix` lacks `.json`, file becomes `top_down_<postfix>_model_context.json`.

### Solvent Properties and Miscibility (legacy Flask)
- POST `/api/solvent`
  - Body (JSON):
    - `solvents` (list, required): e.g., `["water", "ethanol", "acetone"]`
    - `properties` (list, optional): defaults `["Density", "Viscosity"]`
    - `property_sources` (list, optional): any of `["pubchem", "wikipedia", "chemspider"]`; defaults to all
    - `include_miscibility` (bool, optional): default `true`
  - Response (JSON):
    - `properties`: per-source values and a `merged` view (first non-null by source priority)
    - `miscibility`: Sigma-Aldrich-based miscibility matrix if requested
  - Example:
    ```
    curl -X POST http://127.0.0.1:5000/api/solvent \
      -H 'Content-Type: application/json' \
      -d '{
            "solvents": ["water", "ethanol"],
            "properties": ["Density", "Viscosity"],
            "property_sources": ["pubchem", "wikipedia"],
            "include_miscibility": true
          }'
    ```

## Features
### Metagraph
![metagraph](./frontend/assets/img/kg4dt/kg.jpg)
Inspired by the pioneering schema [OntoCAPE](https://www.avt.rwth-aachen.de/cms/avt/forschung/sonstiges/software/~ipts/ontocape/?lidx=1), OntoModel and OntoProcess as ontologies are designed to bridge the gap between model and process knowledge for developing physical model-based chemical process digital twins.

### Agents
![agent](./frontend/assets/img/kg4dt/agent.jpg)
Multiple functional agents are developed to harness the knowledge graph for model assembly, model calibration, rule inference, database access, AI model invocation, and LLM utilisation.
- Available databases: [PubChem](https://pubchem.ncbi.nlm.nih.gov), [ChemSpider](https://www.chemspider.com), and [Wikipedia](https://www.wikipedia.org)
- Example solubility prediction model from the [RMG Group](https://rmg.mit.edu/database/solvation/searchSolubility/)
- [ChatGPT](https://platform.openai.com/settings/organization/api-keys) integrated

## Cases
Prerequisite: KG4DT is locally deployed successfully.
- Bottom-up case: annular microreactor
    - http://127.0.0.1:5000/model/dushman
    - http://127.0.0.1:5000/structure/dushman
    - http://127.0.0.1:5000/application/dushman
        - select <b>dushman</b>, click <b>Import</b>
        - select <b>simulation</b>, click <b>Run</b> to simulate the pristine model
        - select <b>calibration</b> and <math><msub><mi>k</mi><msub><mi>t</mi><mtext>m</mtext></msub></msub></math>, set <b>min</b> to 0.001 and <b>max</b> to 0.01, click <b>Run</b> to calibrate the model
        - select <math><msup><msub><mi>I</mi><mn>3</mn></msub><mo>−</mo></msup></math> to check the result
- Top-down case: Taylor-Couette reactor
    - http://127.0.0.1:5000/knowledge_graph/esterification
        - select <b>top-down</b> mode
        - select <b>esterification</b>, click <b>Import</b>
        - click <b>Infer</b> to proceed rule inference
        - click <b>SPARQL</b> of the <b>Rule</b> card to check SPARQL codes
    - http://127.0.0.1:5000/exploration/esterification
        - select <b>esterification base case</b>, click <b>Import</b>
        - click <b>Run Model Exploration</b> to proceed parallel model calibration
- Amidation reaction optimisation
    - http://127.0.0.1:5000/chatgpt
        - input your own <b>OpenAI API Key</b>. Find information <a href="https://platform.openai.com/settings/organization/api-keys">here</a>
        - click <b>Go</b> to get the answer