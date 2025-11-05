from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _json_error(message: str, status: int = 400, detail: Any | None = None, hint: Any | None = None):
    payload: Dict[str, Any] = {"error": message}
    if detail is not None:
        payload["detail"] = detail
    if hint is not None:
        payload["hint"] = hint
    return payload, status


def _normalize_dataset_section(name: str, section: Dict[str, Any]) -> Dict[str, Any] | Tuple[Dict[str, Any], int]:
    """Normalize a dataset-like section with keys: {"ind": [...], "val"|"value": [[...], ...]}.
    - Ensures indices are tuples for internal processing.
    - Validates that each row has the same number of elements as indices length.
    Returns a normalized dict or (json_error, status) tuple on error.
    """
    if not isinstance(section, dict):
        return _json_error(
            f"Field '{name}' must be an object with 'ind' and 'val' fields.",
            400,
        )

    inds = section.get("ind")
    vals = section.get("val")
    if vals is None and "value" in section:
        vals = section.get("value")

    if not isinstance(inds, list) or not all(isinstance(x, (list, tuple)) for x in inds):
        return _json_error(f"Field '{name}.ind' must be a list of index tuples/lists.", 400)
    if not isinstance(vals, list) or not all(isinstance(row, list) for row in vals):
        return _json_error(
            f"Field '{name}.val' must be a list of rows (lists).",
            400,
            hint={name: {"ind": [["Name", None, None, None, None]], "val": [[1.0]]}},
        )

    n_cols = len(inds)
    for i, row in enumerate(vals):
        if len(row) != n_cols:
            return _json_error(
                f"Row {i} in '{name}.val' has length {len(row)} but expected {n_cols} per '{name}.ind'.",
                400,
            )

    return {"ind": [tuple(ind) for ind in inds], "val": vals}


def simulate_table(context: Dict[str, Any], op_params: Dict[str, Any]) -> Dict[str, Any] | Tuple[Dict[str, Any], int]:
    """Lightweight deterministic simulation over a table of experiments.

    This placeholder computes a single scalar output per experiment by summing all
    numeric values in the corresponding op_params row. Non-numeric values are ignored.

    Input:
      - context: dict (currently unused; reserved for future model-aware simulation)
      - op_params: {"ind": [[...indexes...], ...], "val": [[v11, v12, ...], ...]}

    Output:
      {
        "simulated": {
          "ind": [[...same as input op_params.ind...], ...],
          "val": [[y1], [y2], ...]
        },
        "count": <int>
      }
    """
    if not isinstance(context, dict):
        return _json_error("Field 'context' is required and must be an object.", 400)
    norm = _normalize_dataset_section("op_params", op_params)
    if isinstance(norm, tuple):
        # (error_json, status)
        return norm

    inds: List[tuple] = norm["ind"]
    rows: List[List[Any]] = norm["val"]

    out_vals: List[List[float]] = []
    for row in rows:
        s = 0.0
        for v in row:
            try:
                # Allow ints/floats and numeric strings
                if isinstance(v, (int, float)):
                    s += float(v)
                elif isinstance(v, str):
                    s += float(v) if v.strip() != "" else 0.0
            except Exception:
                # ignore non-numeric cells
                pass
        out_vals.append([s])

    return {"simulated": {"ind": inds, "val": out_vals}, "count": len(out_vals)}
