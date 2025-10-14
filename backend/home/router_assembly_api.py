import datetime as dt
from typing import Any, Dict, List, Set, Tuple

from flask import jsonify, request

from . import blueprint

# DB models (optional at runtime)
try:
    from ..models import get_session
    from ..models.reactor import Reactor
    from ..models.species_role import SpeciesRole
except Exception:  # pragma: no cover - if models are not initialized
    get_session = None  # type: ignore
    Reactor = None      # type: ignore
    SpeciesRole = None  # type: ignore


# -------------------------------
# Helpers & serializers
# -------------------------------

def _reactor_to_dict(r: Any) -> Dict[str, Any]:
    return {
        "id": getattr(r, "id", None),
        "name": getattr(r, "name", None),
        "number_of_input": getattr(r, "number_of_input", None),
        "number_of_output": getattr(r, "number_of_output", None),
        "created_date": (
            getattr(r, "created_date", None).isoformat() if getattr(r, "created_date", None) else None
        ),
        "icon": getattr(r, "icon", None),
        "species": getattr(r, "species", None),
    }


def _default_reactor() -> Dict[str, Any]:
    return {
        "id": 0,
        "name": "Default Reactor",
        "number_of_input": 2,
        "number_of_output": 1,
        "created_date": dt.datetime.utcnow().isoformat() + "Z",
        "icon": None,
        "species": {"example": True, "species": ["A", "B", "C"]},
    }


def _get_pagination_params() -> tuple[int, int]:
    """Parse limit and offset from query params with sane defaults and caps."""
    try:
        limit = int(request.args.get("limit", 100))
    except Exception:
        limit = 100
    try:
        offset = int(request.args.get("offset", 0))
    except Exception:
        offset = 0
    # Enforce bounds
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500
    if offset < 0:
        offset = 0
    return limit, offset


# -------------------------------
# Routes
# -------------------------------

@blueprint.route("/api/model/assembly/reactor_list", methods=["GET"])  
def api_assembly_reactor_list():
    """
    List Reactor records with optional pagination and sorting.

    Query params:
    - limit: int (default 100, max 500)
    - offset: int (default 0)
    - order_by: one of [id, name, created_date, number_of_input, number_of_output]
    - order_dir: asc|desc (default asc)

    If database is not available, returns one default item for testing.
    """
    try:
        limit, offset = _get_pagination_params()
        order_by = (request.args.get("order_by") or "id").strip()
        order_dir = (request.args.get("order_dir") or "asc").lower()
        allowed_fields = {"id", "name", "created_date", "number_of_input", "number_of_output"}
        if order_by not in allowed_fields:
            order_by = "id"
        if order_dir not in {"asc", "desc"}:
            order_dir = "asc"

        items: List[Dict[str, Any]] = []
        db_ok = False

        if get_session and Reactor:
            session = get_session()
            try:
                q = session.query(Reactor)  # type: ignore[attr-defined]
                # Safe ordering
                col = getattr(Reactor, order_by)
                q = q.order_by(col.desc() if order_dir == "desc" else col.asc())
                q = q.offset(offset).limit(limit)
                rows = q.all()
                items = [_reactor_to_dict(r) for r in rows]
                db_ok = True
            except Exception:
                db_ok = False
            finally:
                try:
                    session.close()
                except Exception:
                    pass

        if not db_ok:
            # Provide a single default record if DB isn't connected/ready
            default_items = [_default_reactor()]
            # Apply offset/limit trivially
            items = default_items[offset:offset + limit]

        return jsonify({
            "reactors": items,
            "count": len(items),
            "source": ("db" if db_ok else "default")
        }), 200

    except Exception as e:
        return jsonify({"error": "Internal server error while listing reactors.", "detail": str(e)}), 500


@blueprint.route("/api/model/assembly/list_species_role", methods=["GET"])  
def api_assembly_list_species_role():
    """
    List SpeciesRole records with optional pagination and sorting.

    Query params:
    - limit: int (default 100, max 500)
    - offset: int (default 0)
    - order_by: one of [id, name, attribute]
    - order_dir: asc|desc (default asc)
    """
    try:
        limit, offset = _get_pagination_params()
        order_by = (request.args.get("order_by") or "id").strip()
        order_dir = (request.args.get("order_dir") or "asc").lower()
        allowed_fields = {"id", "name", "attribute"}
        if order_by not in allowed_fields:
            order_by = "id"
        if order_dir not in {"asc", "desc"}:
            order_dir = "asc"

        items: List[Dict[str, Any]] = []
        source = "db"

        if get_session and SpeciesRole:
            session = get_session()
            try:
                q = session.query(SpeciesRole)  # type: ignore[attr-defined]
                col = getattr(SpeciesRole, order_by)
                q = q.order_by(col.desc() if order_dir == "desc" else col.asc())
                q = q.offset(offset).limit(limit)
                rows = q.all()
                for r in rows:
                    items.append({
                        "id": r.id,
                        "name": r.name,
                        "attribute": r.attribute,
                    })
            except Exception:
                source = "unavailable"
                items = []
            finally:
                try:
                    session.close()
                except Exception:
                    pass
        else:
            source = "unavailable"

        return jsonify({
            "species_roles": items,
            "count": len(items),
            "source": source
        }), 200

    except Exception as e:
        return jsonify({"error": "Internal server error while listing species roles.", "detail": str(e)}), 500


@blueprint.route("/api/model/assembly/compute_reactor", methods=["POST"]) 
def api_assembly_compute_reactor():
    """
    Perform a lightweight computation using the provided JSON structure of inputs and a reactor.

    Aggregates:
      - number of input streams
      - list of stream names
      - union of species and reactions
      - combined min/max of operation ranges (temperature, pressure, agitation)

    Returns JSON-safe lists for ranges.
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Unsupported Media Type. Use Content-Type: application/json."}), 415

        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body; expected an object."}), 400

        inputs = payload.get("input")
        reactor = payload.get("reactor")
        if not isinstance(inputs, list) or not isinstance(reactor, dict):
            return jsonify({"error": "Fields 'input' (list) and 'reactor' (object) are required."}), 400

        # Collect stream names and their contents
        stream_names: List[str] = []
        all_species: Set[str] = set()
        all_reactions: Set[str] = set()
        warnings: List[str] = []

        # Helper to merge operation ranges
        def normalize_pair(rng: List[Any] | Tuple[Any, Any] | None) -> Tuple[float | None, float | None]:
            if not rng or not isinstance(rng, (list, tuple)) or len(rng) != 2:
                return (None, None)
            try:
                a = float(rng[0])
                b = float(rng[1])
            except Exception:
                return (None, None)
            low, high = (a, b) if a <= b else (b, a)
            return low, high

        def merge_range(
            acc: Tuple[float | None, float | None], rng: List[Any] | Tuple[Any, Any] | None
        ) -> Tuple[float | None, float | None]:
            low, high = normalize_pair(rng)
            cur_min, cur_max = acc
            if low is not None:
                if cur_min is None or low < cur_min:
                    cur_min = low
            if high is not None:
                if cur_max is None or high > cur_max:
                    cur_max = high
            return cur_min, cur_max

        temp_range: Tuple[float | None, float | None] = (None, None)
        pres_range: Tuple[float | None, float | None] = (None, None)
        agit_range: Tuple[float | None, float | None] = (None, None)

        def extract_and_merge(node: Dict[str, Any]):
            nonlocal temp_range, pres_range, agit_range
            op = node.get("operation", {}) if isinstance(node, dict) else {}
            if not isinstance(op, dict):
                return
            temp = op.get("temperature")
            pres = op.get("pressure")
            agit = op.get("agitation")
            temp_range = merge_range(temp_range, temp)
            pres_range = merge_range(pres_range, pres)
            agit_range = merge_range(agit_range, agit)

            chem = node.get("chemistry", {}) if isinstance(node, dict) else {}
            if isinstance(chem, dict):
                sp = chem.get("species")
                rxn = chem.get("reactions")
                if isinstance(sp, list):
                    for s in sp:
                        if isinstance(s, str):
                            all_species.add(s)
                        else:
                            warnings.append("Non-string species ignored")
                if isinstance(rxn, list):
                    for r in rxn:
                        if isinstance(r, str):
                            all_reactions.add(r)
                        else:
                            warnings.append("Non-string reaction ignored")

        # Process inputs: expect each element is a dict with a single key name -> object
        for idx, entry in enumerate(inputs):
            if not isinstance(entry, dict) or not entry:
                warnings.append(f"Input[{idx}] is not a non-empty object; skipped")
                continue
            # each entry expected to have one name key
            for k, v in entry.items():
                if isinstance(k, str):
                    stream_names.append(k)
                else:
                    warnings.append(f"Input[{idx}] stream name is not a string; skipped name")
                if isinstance(v, dict):
                    extract_and_merge(v)
                else:
                    warnings.append(f"Input[{idx}] stream details is not an object; skipped details")

        # Process reactor
        if isinstance(reactor, dict):
            extract_and_merge(reactor)

        def to_list_pair(p: Tuple[float | None, float | None]) -> List[float]:
            a, b = p
            out: List[float] = []
            if a is not None and b is not None:
                out = [a, b]
            elif a is not None:
                out = [a, a]
            elif b is not None:
                out = [b, b]
            return out

        result = {
            "status": "computed",
            "timestamp": dt.datetime.utcnow().isoformat() + "Z",
            "input_count": len(stream_names),
            "stream_names": stream_names,
            "unique_species": sorted(all_species),
            "unique_reactions": sorted(all_reactions),
            "operation_ranges": {
                "temperature": to_list_pair(temp_range),
                "pressure": to_list_pair(pres_range),
                "agitation": to_list_pair(agit_range),
            },
        }
        if warnings:
            result["warnings"] = warnings

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": "Internal server error while computing reactor summary.", "detail": str(e)}), 500
