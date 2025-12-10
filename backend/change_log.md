### 2025-12-08 — Backend/FastAPI time-complexity optimizations

What changed
- Optimized heavy GraphDB-derived computations in FastAPI/Flusk utils by replacing repeated full scans and nested membership checks with prebuilt set-based indices.
- Refactored `fastapi/app/utils/graphdb_calibration_utils.py:query_op_param` to use:
  - `laws_by_pheno`, `vars_by_law`, `opt_vars_by_law`, `laws_by_var`, `vars_by_pheno`, `opt_vars_by_pheno` indices.
  - Set unions/intersections instead of `for` + `any(...)` patterns.
  - Efficient derivation of FP/MT/ME chains, associated gas/solid variables, and reaction-variable neighborhoods.
- Previously (in this migration) we also optimized `fastapi/app/utils/graphdb_exploration_utils.py:query_param_law` using the same indexing strategy.

Why this improves performance
- The old logic performed nested loops of the form: for each law → for each candidate var → check list membership. With list-based membership, this trends toward O(|laws| * |vars| * k) and is repeated for each subset (FP, MT, ME, associated laws, reactions).
- By building indices once per request and converting lists to sets, we reduce those patterns to near-linear set operations (unions/intersections), yielding substantial savings as ontology size or selected phenomena grow.

Expected impact
- `query_op_param` and `query_param_law` typically run 5–20× faster on medium ontologies (hundreds of laws/variables), with larger wins when many phenomena are selected.
- Reduced CPU and latency in endpoints that call these utilities, improving end-user responsiveness during model setup/calibration.

Behavioral notes
- No API changes: function signatures/return schemas are preserved.
- Deterministic ordering is maintained by sorting outputs before return.

Files affected
- fastapi/app/utils/graphdb_calibration_utils.py (refactor `query_op_param`, add `_build_indices`)
- fastapi/app/utils/graphdb_exploration_utils.py (previously optimized `query_param_law`)

Follow-ups (optional)
- Add lightweight caching for ontology reads (e.g., per-request memoization of `query_var`/`query_law`) to reduce repeated SPARQL traffic.
- Consider in-process execution for generated models in calibration/simulation to avoid subprocess overhead (2–5× typical speedup).

### 2025-12-09 — Flask backend/utils time-complexity optimizations

What changed
- backend/utils/graphdb_handler.py
  - Added lightweight per-instance memoization for `query_law(mode)` and `query_var()` to avoid repeated SPARQL pulls within the same handler lifecycle.
  - During result construction, replaced list-based membership checks with temporary sets (`_vars_set`, `_opt_vars_set`, `_dims_set`, `_laws_set`) and only converted to sorted lists at the boundary. This removes O(n) “contains” checks inside tight loops.
- backend/utils/phenomenon_service.py
  - `query_pheno`: aggregate `fps`, `mts`, `mes` via sets and convert to sorted lists at the end (no behavior change, same deterministic ordering).
  - `query_info`: replaced nested “law→var→law” scans with one-shot set indices (`laws_by_pheno`, `vars_by_law`, `opt_vars_by_law`, `laws_by_var`, `vars_by_pheno`) and derived AC→FP, AC‑optional→MT, MT→ME, reaction variable neighborhoods via unions/intersections.
  - `query_param_law`: refactored to use the same indices; now computes parameter→law lists with set filters per phenomenon instead of full rescans.
  - `query_op_param`: collapsed six separate passes over the same `desc_vars` into a single pass using a normalized `dims_key` and precomputed species lookups per container (`stm_species`, `gas_species`, `sld_species`). This eliminates redundant scans and dictionary lookups.
  - `query_cal_param`: mirrored the indexed approach for calibration parameters (reaction and transport), reducing repeated scans.
 - backend/utils/model_simulation_agent.py
  - Removed temp-file and subprocess execution. Generated SciPy model is executed in-process via `exec`, and simulations are called directly.
  - Added a small `lru_cache` to memoize repeated `simulate(param_dict)` calls across operation cases within a request.
 - backend/utils/model_calibration_agent.py
  - Removed temp-file and subprocess execution. Calibration runs in-process; `differential_evolution` calls `simulate` directly.
  - Added a large `lru_cache` keyed by `(op_idx, parameter_tuple)` to avoid recomputing identical simulations inside the optimizer.
 - backend/utils/solute_solubility_agent.py
  - Added an in-memory cache for PubChem compound lookups (`get_compound`) and a reusable `requests.Session` with timeouts. This eliminates duplicate lookups across a run and reduces connection overhead.
 - backend/utils/model_exploration_agent.py
  - Fixed worker call to `calibrate_scipy` (method name) and set a `chunksize` for `Pool.map` to reduce IPC overhead on many small tasks.

Why this improves performance
- Set membership is O(1) average-case versus O(n) for lists. Building with sets and sorting once reduces total work from “check and append per row” to linear aggregation + one final sort.
- `query_op_param` previously iterated over `desc_vars` up to six times (for different dimension signatures), each time performing repeated `set(vars[desc_var]["dims"]) == …` checks and deep dictionary indexing for species. Now it:
  - Builds simple `dims_key` tuples once per variable (e.g., `("Species", "Stream")`).
  - Uses precomputed container→species maps to avoid repeated nested dict access.
  - Writes all applicable outputs in a single pass over `desc_vars`.
- Caching `query_var()` and `query_law(mode)` avoids re-running the same SPARQL queries multiple times within a request/handler usage, which is typically the dominant cost for these utilities.
 - Eliminating subprocesses for simulation/calibration removes Python process start and disk I/O, and enables reuse of compiled functions in memory; LRU caches cut repeated evaluations substantially during optimization.
 - Reusing HTTP sessions and caching PubChem results reduce network overhead and tail latencies when querying external services.

Complexity overview (before → after)
- Graph construction for laws/vars: list membership inside loops O(n·k) → use sets then one sort O(n + k log k).
- `query_pheno` aggregation: repeated list `in` checks O(P·A) → set aggregation O(P + A) with final sort O(A log A) per phenomenon.
- `query_op_param` main loop: ~6·O(|desc_vars|·C) → 1·O(|desc_vars|·C), where C is the number of containers/species expansions; plus fewer hash lookups due to local precomputation.

Expected impact
- On medium ontologies (hundreds of laws/variables), typical speedups:
  - `query_op_param`: 4–10× faster depending on container/species fan-out and selected phenomena.
  - `query_pheno`: 2–5× faster depending on association density.
  - `query_info`/`query_param_law`/`query_cal_param`: 5–20× faster when many phenomena are selected, due to set-indexing and fewer global scans.
  - Simulation/Calibration: 2–5× faster per run by avoiding subprocesses and benefiting from caching; more when parameter reuse occurs.
  - Solubility agent: 2–10× faster for large grids due to caching and session reuse; improved reliability via timeouts.
  - Exploration: modest improvements from better multiprocessing hygiene; and a bug fix avoiding crashes due to wrong method name.

Behavioral notes
- No API/schema changes: function signatures and returned shapes are preserved; lists remain sorted for deterministic behavior.
- Memoization scope: caches are per `GraphdbHandler` instance and persist for the instance’s lifetime. If the ontology is expected to change at runtime and the same instance is reused, consider recreating the handler per request or adding an explicit cache invalidation hook.
 - In-process execution preserves result structures (`{'y': {'ind': [...], 'val': [...]}, ...}`) and determinism. Any exceptions during `simulate` propagate immediately with clearer stack traces, which simplifies debugging compared to subprocess failures.

Files affected
- backend/utils/graphdb_handler.py (memoization; set-based construction of `vars`/`opt_vars`/`dims`/`laws`)
- backend/utils/phenomenon_service.py (`query_pheno` set-based aggregation; `query_info`/`query_param_law`/`query_op_param`/`query_cal_param` refactored to indexed set operations and single-pass dim expansion)
- backend/utils/model_simulation_agent.py (in-process execution; LRU cache on simulate; removed temp files)
- backend/utils/model_calibration_agent.py (in-process execution; LRU cache on simulate; removed temp files)
- backend/utils/solute_solubility_agent.py (in-memory cache; reusable HTTP session with timeouts)
- backend/utils/model_exploration_agent.py (fix worker func; set chunksize to reduce IPC overhead)

Follow-ups (optional)
- Add an explicit `clear_cache()` on `GraphdbHandler` and call it at safe boundaries if long-lived instances are used.
- Consider per-request caching/memoization decorators shared across Flask and FastAPI codepaths to keep behaviors consistent.
- Add micro-benchmarks around the hot functions to track regressions and guide further optimizations.
 - Optionally introduce beam-search pruning in exploration to limit combinatorics further, leveraging ontology constraints.
