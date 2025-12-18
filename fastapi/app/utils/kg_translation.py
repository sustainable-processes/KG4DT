from __future__ import annotations

from typing import Any, Dict


def translate_descriptor_section(section: Dict[str, Any] | None) -> Dict[str, Any]:
    """Translate KG descriptor maps (st/op) into frontend placeholders.

    Rules:
      - If descriptor type == "range" -> {"max": 0, "min": 0}
      - If descriptor type == "value" (or anything else) -> 0
    Unknown or non-dict entries are ignored.
    """
    result: Dict[str, Any] = {}
    if not isinstance(section, dict):
        return result
    for name, desc in section.items():
        if not isinstance(desc, dict):
            continue
        typ = (desc.get("type") or "value").lower()
        if typ == "range":
            result[name] = {"max": 0, "min": 0}
        else:
            result[name] = 0
    return result


def build_frontend_from_kg_context(ctx_name: str, ctx_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build the frontend JSON for a single KG context entry.

    Output shape:
      {
        "<ctx_name>": {
          "source": [],
          "utility": [],
          "chemistry": {},
          "operation": { ... },
          "structure": { ... },
          "phenomenon": {},
          "destination": []
        }
      }
    """
    structure = translate_descriptor_section(ctx_data.get("st"))
    operation = translate_descriptor_section(ctx_data.get("op"))

    entry = {
        "source": [],
        "utility": [],
        "chemistry": {},
        "operation": operation,
        "structure": structure,
        "phenomenon": {},
        "destination": [],
    }
    return {ctx_name: entry}


__all__ = [
    "translate_descriptor_section",
    "build_frontend_from_kg_context",
]
